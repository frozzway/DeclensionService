from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from enum import Enum


class Case(Enum):
    nomn = "именительный"
    gent = "родительный"
    datv = "дательный"
    accs = "винительный"
    ablt = "творительный"
    loct = "предложный"
    voct = "звательный"
    gen2 = "второй родительный (частичный)"
    acc2 = "второй винительный"
    loc2 = "второй предложный (местный)"


class Gender(Enum):
    masc = "мужской род"
    femn = "женский род"
    neut = "средний род"


class Number(Enum):
    sing = "единственное число"
    plur = "множественное число"


cases = {case.name: case.value for case in Case}
genders = {gender.name: gender.value for gender in Gender}
numbers = {number.name: number.value for number in Number}


def display_values(data: dict):
    return '<br>'.join((f'{key} - {val}' for key, val in data.items()))


class CommonResult(BaseModel):
    result: str = Field(description='Результирующий текст')


class Declension(BaseModel):
    case: Literal[tuple(cases.keys())] = Field(description=f'Падеж. Принимает значения:<br>{display_values(cases)}')
    gender: Optional[Literal[tuple(genders.keys())]] = Field(default=None, description=f'Пол Принимает значения:<br>{display_values(genders)}')
    number: Optional[Literal[tuple(numbers.keys())]] = Field(default=Number.sing.name, description=f'Число. Принимает значения:<br>{display_values(numbers)}')
    system: Optional[str] = Field(default=None, description='Наименование системы')


class PersonNameDeclension(Declension):
    fullname: str = Field(min_length=1, description='Текст на склонение')

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "fullname": "Пельмешкин Орех Орехович",
                    "case": Case.gent.name,
                    "gender": Gender.masc.name,
                    "number": Number.sing.name,
                    "system": "ГКУ"
                }
            ]
        }
    }


class TextDeclension(Declension):
    source_text: str = Field(min_length=1, description='Текст на склонение')


class DeclensionException(TextDeclension):
    id: int = Field(description='Идентификатор исключения')
    result: str = Field(description='Результирующий текст')

    model_config = ConfigDict(from_attributes=True)


class DeclensionExceptionCreate(TextDeclension):
    target_text: str = Field(description='Результирующий текст')


class DeclensionExceptionUpdate(TextDeclension):
    result: str = Field(description='Результирующий текст')
