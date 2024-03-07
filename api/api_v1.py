from fastapi import APIRouter, status, Depends

from models import PersonNameDeclension, TextDeclension, CommonResult, DeclensionExceptionCreate, DeclensionException
from services import DeclensionNameService, DeclensionTextService, DeclensionExceptionsService


router = APIRouter()


@router.post(
    "/person_name",
    response_model=CommonResult,
    description="Склонение имен, фамилий"
)
async def decline_person_name(
    request: PersonNameDeclension,
    declension_service: DeclensionNameService = Depends()
):
    return await declension_service.get_inflected_person_name(request)


@router.post(
    "/",
    response_model=CommonResult,
    description="Склонение общих слов",

)
async def decline_text(
    request: TextDeclension,
    declension_service: DeclensionTextService = Depends()
):
    return await declension_service.get_inflected_text(request)


@router.post(
    "/add_exception",
    status_code=status.HTTP_201_CREATED,
    response_model=DeclensionException,
    description="Добавить исключение"
)
async def add_exception(
    request: DeclensionExceptionCreate,
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.create_exception(request)


@router.get(
    '/systems',
    response_model=list[str],
    description="Возвращает имена систем"
)
async def list_systems(
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.list_systems()
