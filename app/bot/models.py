from dataclasses import dataclass

from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import db
from app.quiz.models import Question
from sqlalchemy import (
    Column,
    BigInteger,
    VARCHAR,
    ForeignKey, ForeignKeyConstraint,
    Index,
    Boolean,
)


@dataclass
class User:
    id: int
    uname: str | None = None


@dataclass
class UserChat:
    id: int
    chat_id: int
    uname: str | None = None


@dataclass
class LastSession:
    lead: User
    completed_questions: int
    correct_questions: int


@dataclass
class SessionQuestion:
    question: Question
    started_date: int
    completed_questions: int
    correct_questions: int
    lead: User
    respondent: User | None = None


@dataclass
class BotSession:
    chat_id: int
    session_question: SessionQuestion | None = None
    last_session: LastSession | None = None

    def check_answer(self, ans: str):
        return self.session_question and any(ans in a for a in self.session_question.question.answers)


class SessionModel(db):
    __tablename__ = "sessions"
    chat_id = Column(BigInteger, primary_key=True, index=True, unique=True)
    session_question = relationship("SessionCurrentQuestionModel", back_populates="session", uselist=False)
    session_last = relationship("LastSessionModel", back_populates="session", uselist=False)


class SessionCurrentQuestionModel(db):
    __tablename__ = "sessions_question"
    session_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), nullable=False, index=True,
                        primary_key=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    started_date = Column(BigInteger, nullable=False)
    lead = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))
    completed_questions = Column(BigInteger, default=0)
    correct_questions = Column(BigInteger, default=0)
    session = relationship("SessionModel", back_populates="session_question")
    question = relationship("QuestionModel")
    tg_users = relationship("TgUsersModel", back_populates="sessions")


class AnswerResponseStageModel(db):
    __tablename__ = "response_stage"
    session_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), nullable=False, index=True,
                        primary_key=True)
    respondent = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))


class LastSessionModel(db):
    __tablename__ = "last_session"
    session_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), nullable=False, index=True,
                        primary_key=True)
    lead = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))
    completed_questions = Column(BigInteger)
    correct_questions = Column(BigInteger)
    session = relationship("SessionModel", back_populates="session_last")


class TgChatUsersModel(db):
    __tablename__ = "tg_chat_users"
    chat_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), index=True, primary_key=True)
    id = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"), primary_key=True)
    tg_user = relationship("TgUsersModel", back_populates="tg_user_chat")


class TgUsersModel(db):
    __tablename__ = "tg_users"
    id = Column(BigInteger, primary_key=True, index=True)
    uname = Column(VARCHAR(256))
    tg_user_chat = relationship("TgChatUsersModel", back_populates="tg_user")
    sessions = relationship("SessionCurrentQuestionModel", back_populates="tg_users")
