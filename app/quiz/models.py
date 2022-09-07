from dataclasses import dataclass
from app.store.database.sqlalchemy_base import db
from sqlalchemy.orm import relationship
from typing import Optional

from sqlalchemy import (
    Column,
    BigInteger,
    VARCHAR,
    ForeignKey, ForeignKeyConstraint,
    Index,
    Boolean,
)


@dataclass
class Theme:
    id: Optional[int]
    title: str


@dataclass
class Question:
    id: Optional[int]
    title: str
    theme_id: int
    answers: list["Answer"]


@dataclass
class Answer:
    title: str
    is_correct: bool


class ThemeModel(db):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    title = Column(VARCHAR(256), nullable=False, unique=True, index=True)
    question = relationship("QuestionModel")


class QuestionModel(db):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    title = Column(VARCHAR(256), nullable=False, unique=True, index=True)
    theme_id = Column(BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)
    answers = relationship("AnswerModel", back_populates="question")


class AnswerModel(db):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    title = Column(VARCHAR(256), nullable=False)
    is_correct = Column(Boolean(), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question = relationship("QuestionModel", back_populates="answers")
