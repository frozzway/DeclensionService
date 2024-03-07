from fastapi import APIRouter

from .api_v1 import router as v1_router
from .api_exceptions import router as exception_router

router = APIRouter()

router.include_router(v1_router)
router.include_router(exception_router)
