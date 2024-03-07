from fastapi import APIRouter, status, Depends

from models import DeclensionExceptionCreate, DeclensionException, DeclensionExceptionUpdate
from services import DeclensionExceptionsService


router = APIRouter(prefix='/exceptions', tags=['exceptions'])


@router.post(
    "/",
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
    "/",
    response_model=list[DeclensionException],
    description="Вывести все исключения"
)
async def list_all_exceptions(
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.list_all_exceptions()


@router.get(
    "/{system}",
    response_model=list[DeclensionException],
    description="Вывести исключения для одной системы"
)
async def list_exceptions_within_one_system(
    system: str,
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.list_exceptions_within_system(system)


@router.delete(
    "/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Удалить исключение"
)
async def delete_exception(
    exception_id: int,
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.delete_exception(exception_id)


@router.put(
    "/{exception_id}",
    response_model=DeclensionException,
    description="Обновить исключение"
)
async def update_exception(
    exception_id: int,
    request: DeclensionExceptionUpdate,
    declension_service: DeclensionExceptionsService = Depends()
):
    return await declension_service.update_exception(exception_id, request)
