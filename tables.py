from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Sentence(Base):
    __tablename__ = 'sentence'

    id: Mapped[int] = mapped_column(primary_key=True)
    source_text: Mapped[str]
    case: Mapped[str]
    number: Mapped[str] = mapped_column(nullable=True)
    gender: Mapped[str] = mapped_column(nullable=True)
    result: Mapped[str]
    create_datetime: Mapped[datetime] = mapped_column(insert_default=func.now())
    system: Mapped[str] = mapped_column(nullable=True)
