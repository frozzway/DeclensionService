import pytest, pytest_asyncio

from httpx import AsyncClient

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker
from fastapi import status, FastAPI

from app import app
from database import get_session
from tables import Base
from settings import settings
from utils.casing_manager import get_words_casing, apply_words_cases, apply_cases


url_object_to_test_db = URL.create(
    settings.db_dialect,
    username=settings.db_username,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.test_database,
)

engine = create_async_engine(url_object_to_test_db, poolclass=NullPool)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def get_test_session():
    session = Session()
    await session.begin()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture(scope="session")
async def test_application() -> FastAPI:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_session] = get_test_session
    yield app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(test_application) -> AsyncClient:
    client = AsyncClient(app=test_application, base_url="http://test")
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def declension_exception(client) -> int:
    response = await client.post("exceptions/", json={
        'source_text': 'Мерзлячкин Арбуз Арбузович',
        'case': 'gent',
        'gender': 'masc',
        'target_text': 'Мерзлячкину Арбуз Арбузовичу',
        'system': 'Тест'
    })
    entity_id = int(response.json()['id'])
    yield entity_id
    await client.delete(f"exceptions/{entity_id}")


class TestDeclensionExceptions:
    @pytest.mark.anyio
    async def test_declension_creation_and_using(self, client):
        response = await client.post("exceptions/", json={
            'source_text': 'Пельмешкин Орех Орехович',
            'case': 'gent',
            'target_text': 'Пельмешкину Орех Ореховичу',
            'system': 'Тест'
        })
        assert response.status_code == status.HTTP_201_CREATED
        entity_id = int(response.json()['id'])

        response = await client.post("/person_name", json={
            'fullname': 'Пельмешкин Орех Орехович',
            'case': 'gent',
            'system': 'Тест'
        })
        expected_result = 'Пельмешкину Орех Ореховичу'
        assert response.json()['result'] == expected_result

        response = await client.delete(f"exceptions/{entity_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.anyio
    async def test_declension_with_gender_exception(self, declension_exception, client):
        response = await client.post("/person_name", json={
            'fullname': 'Мерзлячкин Арбуз Арбузович',
            'case': 'gent',
            'gender': 'masc',
            'system': 'Тест'
        })
        expected_result = 'Мерзлячкину Арбуз Арбузовичу'
        assert response.json()['result'] == expected_result

        response = await client.post("/person_name", json={
            'fullname': 'Мерзлячкин Арбуз Арбузович',
            'case': 'gent',
            'system': 'Тест'
        })
        expected_result = 'Мерзлячкина Арбуза Арбузовича'
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_declension_wrong_system(self, declension_exception, client):
        response = await client.post("/person_name", json={
            'fullname': 'Мерзлячкин Арбуз Арбузович',
            'case': 'gent',
            'gender': 'masc',
            'system': 'Система которой нет'
        })
        expected_result = 'Мерзлячкина Арбуза Арбузовича'
        assert response.json()['result'] == expected_result


class TestDeclensionText:
    @pytest.mark.anyio
    async def test_date_with_month_as_word(self, client):
        response = await client.post('/', json={
            'source_text': "21 августа 2021",
            'case': 'gent'
        })
        expected_result = "21 августа 2021"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_inflected_text(self, client):
        response = await client.post('/', json={
            'source_text': "Иванов Иван Иванович",
            'case': 'gent'
        })
        expected_result = "Иванова Ивана Ивановича"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_complex_name(self, client):
        response = await client.post('/', json={
            'source_text': "Сибирский торгово-промышленный",
            'case': 'datv',
            'number': 'plur'
        })
        expected_result = "Сибирским торгово-промышленным"
        assert response.status_code == 200
        assert response.json()['result'] == expected_result


class TestDeclensionPersonName:
    @pytest.mark.anyio
    async def test_inflected_person_name_by_fullname(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Хероведов Андрей Михайлович",
            'case': 'datv'
        })
        expected_result = "Хероведову Андрею Михайловичу"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_case_1(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Шишь Алёна Алексеевна",
            'case': 'datv'
        })
        expected_result = "Шишь Алёне Алексеевне"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_case_2(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Шишь Алёна Алексеевна",
            'case': 'gent'
        })
        expected_result = "Шишь Алёны Алексеевны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_case_3(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Сидорова Ольга Ларисовна",
            'case': 'datv'
        })
        expected_result = "Сидоровой Ольге Ларисовне"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_case_4(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Сидорова Ольга Ларисовна",
            'case': 'gent'
        })
        expected_result = "Сидоровой Ольги Ларисовны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_inflected_person_separated_name_parts(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Охременко Алёна",
            'case': 'datv'
        })
        expected_result = "Охременко Алёне"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_empty_name(self, client):
        response = await client.post('/person_name', json={
            'fullname': "",
            'case': 'datv'
        })
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_male_surname_end(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Шкитин Владимир Александрович",
            'case': 'gent'
        })
        expected_result = "Шкитина Владимира Александровича"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_male_surname_ends_o(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Фещенко Юрий Николаевич",
            'case': 'gent'
        })
        expected_result = "Фещенко Юрия Николаевича"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_male_surname_ends_j(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Полишевский Владимир Владимирович",
            'case': 'gent'
        })
        expected_result = "Полишевского Владимира Владимировича"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_end_1(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Пимнева Елена Евгеньевна",
            'case': 'gent'
        })
        expected_result = "Пимневой Елены Евгеньевны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_end_2(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Колышкина Анна Евгеньевна",
            'case': 'datv'
        })
        expected_result = "Колышкиной Анне Евгеньевне"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_end_3(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Шадрина Ольга Витальевна",
            'case': 'gent'
        })
        expected_result = "Шадриной Ольги Витальевны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_surname_ends_aya_1(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Хашковская Влада Владимиовна",
            'case': 'gent'
        })
        fullname = "Хашковская Влада Владимиовна"
        expected_result = "Хашковской Влады Владимиовны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_surname_ends_aya_2(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Хашковская Влада Владимиовна",
            'case': 'datv'
        })
        expected_result = "Хашковской Владе Владимиовне"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_surname_ends_ora(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Гамора Ольга Витальевна",
            'case': 'gent'
        })
        expected_result = "Гаморы Ольги Витальевны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_surname_ends_ina_1(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Злобина Олеся Викторовна",
            'case': 'gent'
        })
        expected_result = "Злобиной Олеси Викторовны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_female_surname_ends_ina_2(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Зеленкина Яна Николаевна",
            'case': 'gent'
        })
        expected_result = "Зеленкиной Яны Николаевны"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_male_ends_ov_ev_1(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Лежнев Дмитрий Михайлович",
            'case': 'ablt'
        })
        expected_result = "Лежневым Дмитрием Михайловичем"
        assert response.json()['result'] == expected_result

    @pytest.mark.anyio
    async def test_male_ends_ov_ev_2(self, client):
        response = await client.post('/person_name', json={
            'fullname': "Филиппов Дмитрий Михайлович",
            'case': 'ablt'
        })
        expected_result = "Филипповым Дмитрием Михайловичем"
        assert response.json()['result'] == expected_result


class TestCasingManager:

    def test_get_words_casing(self):
        text = "HelLo WoRlD"
        result = get_words_casing(text.split())
        expected_result = [[False, True, True, False, True],
                           [False, True, False, True, False]]
        assert expected_result == result

    def test_apply_words_cases(self):
        text = "HelLo WoRlD"
        new_text = "hello, world!"
        words_cases = get_words_casing(text.split())
        expected_result = ["HelLo,", "WoRlD!"]
        result = apply_words_cases(new_text.split(), words_cases)
        assert expected_result == result

    def test_apply_cases(self):
        source_text = "ООО Пельмень Иван"
        target_text = "ооо пельменю ивану"
        expected_result = "ООО Пельменю Ивану"
        result = apply_cases(source_text, target_text)
        assert expected_result == result