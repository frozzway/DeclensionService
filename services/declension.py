from typing import Optional, Iterable, Annotated

import pymorphy3
from fastapi import Depends
from nltk.stem import SnowballStemmer

from models import TextDeclension, CommonResult, PersonNameDeclension, Gender
from settings import settings
from .declension_exceptions import DeclensionExceptionsService
from utils.casing_manager import apply_cases

morph = pymorphy3.MorphAnalyzer(lang='ru')
vowels = ['у', 'е', 'ы', 'э', 'я', 'и', 'ю', 'ь', 'о']
female_names = ["влада"]

ExceptionServiceDependency = Annotated[DeclensionExceptionsService, Depends(DeclensionExceptionsService)]


class InflectionException(Exception):
    pass


def endswith_any(word: str, suffixes: Iterable[str]):
    return any((word.endswith(suffix) for suffix in suffixes))


def get_inflected_word(word: str, options: set[str], raise_on_fail=False, animacy=False) -> Optional[str]:
    """
    :param word: слово к преобразованию
    :param options: параметры преобразования
    :param raise_on_fail: Выбрасывать исключение при ошибке преобразования слова
    :param animacy: Подобрать одушевленную форму слова
    """
    if None in options:
        options.remove(None)
    parsed_words = morph.parse(word)
    if animacy:
        word = next(filter(lambda p: {'NOUN', 'anim', 'nomn'}.issubset(p.tag.grammemes), parsed_words), parsed_words[0])
    else:
        word = parsed_words[0]
    inflected_word = word.inflect(options)
    if not inflected_word and raise_on_fail:
        raise InflectionException()
    return inflected_word.word if inflected_word else word.word


class DeclensionNameService:
    def __init__(self, db: ExceptionServiceDependency):
        self.snowball = SnowballStemmer(language="russian")
        self.db = db

    @staticmethod
    def _get_gender_by_patronymic(patronymic: str) -> str:
        if patronymic.endswith('на'):
            return Gender.femn.name
        return Gender.masc.name

    @staticmethod
    def _get_gender_by_name(name: str) -> str:
        _name_parse_obj = morph.parse(name)[0]
        if _name_parse_obj.word.lower() in female_names:
            return Gender.femn.name
        return _name_parse_obj.tag.gender

    def try_recognize_gender(self, patronymic, name):
        gender = Gender.femn.name
        if patronymic:
            gender = self._get_gender_by_patronymic(patronymic)
        elif name:
            gender = self._get_gender_by_name(name)
        return gender

    async def get_inflected_person_name(self, request: PersonNameDeclension):
        sentence = await self.db.get_single_result_from_db(request.fullname, request)
        if sentence:
            return CommonResult(result=sentence.result)

        surname, name, patronymic = self._get_separated_name(request.fullname)
        if not request.gender:
            request.gender = self.try_recognize_gender(patronymic, name)
        options = {request.case, request.gender, request.number}
        results_words = []

        exceptions = await self.db.get_many_results_from_db([surname, name, patronymic], request)

        if name and surname:
            name = exceptions.get(name) if exceptions.get(name) else get_inflected_word(name, options, animacy=True)

            common_name = settings.male_common_name if request.gender == Gender.masc.name else settings.female_common_name
            template_word = get_inflected_word(common_name, options, animacy=True)

            try:
                inflected_surname = get_inflected_word(surname, options, raise_on_fail=True, animacy=True)
            except InflectionException:
                inflected_surname = None

            if exceptions.get(surname):
                surname = exceptions.get(surname)
            elif endswith_any(surname, ['ов', 'ев', 'ева', 'ина']):
                surname = self._get_ova_eva_case(surname, request.gender, template_word)
            elif surname.endswith("ая"):
                surname = self._get_femn_aya_case(surname, template_word)
            elif surname.endswith("ора") and inflected_surname:
                surname = inflected_surname
            elif surname[-1] in vowels:
                surname = surname.lower()
            elif inflected_surname:
                surname = inflected_surname
            else:
                surname = self._get_rest_cases_surname(surname, template_word)

            results_words = [surname, name]

            if patronymic:
                patronymic = exceptions.get(patronymic) if exceptions.get(patronymic) else get_inflected_word(
                    patronymic, options, animacy=True)
                results_words.append(patronymic)

        elif surname and not name and not patronymic:
            surname = get_inflected_word(surname, options, animacy=True)
            results_words = [surname]

        result = " ".join([x.capitalize() for x in results_words])
        return CommonResult(result=result)

    def _get_ova_eva_case(self, surname: str, gender: str, template_word: str):
        stem_form = self.snowball.stem(template_word)
        ending = template_word[len(stem_form):]
        if gender == Gender.masc.name:
            inflected_surname = surname + ending
        else:
            inflected_surname = surname[:-1] + ending
        return inflected_surname

    def _get_femn_aya_case(self, surname: str, template_word: str):
        stem_form = self.snowball.stem(template_word)
        ending = template_word[len(stem_form):]
        inflected_surname = surname[:-2] + ending
        return inflected_surname

    def _get_rest_cases_surname(self, surname: str, template_word: str) -> str:
        stem_form = self.snowball.stem(template_word)
        ending = template_word[len(stem_form):]
        inflected_surname = self.snowball.stem(surname) + ending
        return inflected_surname

    @staticmethod
    def _get_separated_name(fullname: str):
        words = fullname.split()
        words_count = len(words)
        if words_count >= 2:
            surname = words[0]
            name = words[1]
            if words_count >= 3:
                patronymic = words[2]
                return surname, name, patronymic
            return surname, name, None
        return words[0], None, None


class DeclensionTextService:
    def __init__(self, db: ExceptionServiceDependency):
        self.db = db

    async def get_inflected_text(self, request: TextDeclension) -> CommonResult:
        sentence = await self.db.get_single_result_from_db(request.source_text, request)
        if sentence:
            return CommonResult(result=sentence.result)

        words = request.source_text.split()
        exceptions = await self.db.get_many_results_from_db(words, request)
        options = {request.case, request.gender, request.number}

        inflected_words = []

        for word in words:
            if word in exceptions.keys():
                inflected_words.append(exceptions[word].result)
            else:
                inflected = get_inflected_word(word, options)
                inflected_words.append(inflected)

        target_text = ' '.join(inflected_words)
        return CommonResult(result=apply_cases(request.source_text, target_text))
