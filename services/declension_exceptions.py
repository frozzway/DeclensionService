from typing import Optional, Iterable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from models import DeclensionExceptionCreate, Declension, DeclensionExceptionUpdate
from tables import Sentence
from database import get_session


class DeclensionExceptionsService:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    async def _get_exception(self, exception_id: int) -> Sentence:
        stmt = select(Sentence).where(Sentence.id == exception_id)
        entity = (await self.session.execute(stmt)).scalar()
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return entity

    async def create_exception(self, request: DeclensionExceptionCreate) -> Sentence:
        model = request.model_dump()
        result = model.pop('target_text')
        create_model = model.copy()
        create_model['result'] = result
        sentence = (await self.session.execute(select(Sentence).filter_by(**model))).first()
        if sentence:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)
        sentence = Sentence(**create_model)
        self.session.add(sentence)
        await self.session.commit()
        return sentence

    async def update_exception(self, exception_id: int, request: DeclensionExceptionUpdate) -> Sentence:
        entity = await self._get_exception(exception_id)
        for field, value in request:
            setattr(entity, field, value)
        await self.session.commit()
        return entity

    async def delete_exception(self, exception_id: int):
        entity = await self._get_exception(exception_id)
        await self.session.delete(entity)
        await self.session.commit()

    async def list_all_exceptions(self) -> list[Sentence]:
        stmt = select(Sentence)
        sentences = await self.session.execute(stmt)
        return list(sentences.scalars())

    async def list_exceptions_within_system(self, system: str) -> list[Sentence]:
        stmt = select(Sentence).where(Sentence.system == system)
        sentences = await self.session.execute(stmt)
        return list(sentences.scalars())

    async def list_systems(self) -> list[str]:
        stmt = select(Sentence.system).distinct()
        systems = await self.session.execute(stmt)
        return [s for s in systems.scalars() if s is not None]

    async def get_single_result_from_db(self, text: str, request: Declension) -> Optional[Sentence]:
        clauses = self.construct_where_clauses(request)
        statement = select(Sentence).where(Sentence.source_text == text).where(*clauses)
        result = await self.session.execute(statement)
        return result.scalar()

    async def get_many_results_from_db(self, words: Iterable[str], request: Declension) -> dict[str, Sentence]:
        clauses = self.construct_where_clauses(request)
        statement = select(Sentence).where(Sentence.source_text.in_(words)).where(*clauses)
        result = await self.session.execute(statement)
        return {sentence.source_text: sentence for sentence in result.scalars()}

    @staticmethod
    def construct_where_clauses(request: Declension) -> list[ColumnElement[bool]]:
        clauses = [Sentence.system == request.system,
                   Sentence.gender == request.gender,
                   Sentence.number == request.number,
                   Sentence.case == request.case]
        return clauses
