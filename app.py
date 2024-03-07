from fastapi import FastAPI
from fastapi.routing import APIRoute
from contextlib import asynccontextmanager

import api
from database import engine
from tables import Base


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


tags_metadata = [
    {
        'name': 'default',
        'description': 'v1 API'
    },
    {
        'name': 'exceptions',
        'description': 'Работа с исключениями'
    }
]

app = FastAPI(openapi_tags=tags_metadata, title='Сервис склонений', lifespan=lifespan)
app.include_router(api.router)
use_route_names_as_operation_ids(app)
