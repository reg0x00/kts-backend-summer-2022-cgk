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
class Question:
    id: Optional[int]
    title: str
    answers: list["Answer"]


@dataclass
class Answer:
    title: str


class QuestionModel(db):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    title = Column(VARCHAR(256), nullable=False, unique=True, index=True)
    answers = relationship("AnswerModel", back_populates="question")


class AnswerModel(db):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    title = Column(VARCHAR(256), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question = relationship("QuestionModel", back_populates="answers")
