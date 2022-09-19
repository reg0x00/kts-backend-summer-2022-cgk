from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import db
from sqlalchemy import (
    Column,
    BigInteger,
    VARCHAR,
    ForeignKey,
)


class SessionModel(db):
    __tablename__ = "sessions"
    chat_id = Column(BigInteger, primary_key=True)
    session_question = relationship("SessionCurrentQuestionModel", back_populates="session", uselist=False)
    session_last = relationship("LastSessionModel", back_populates="session", uselist=False)
    tg_users = relationship("TgUserChatModel", back_populates="sessions")


class SessionCurrentQuestionModel(db):
    __tablename__ = "sessions_question"
    session_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"),
                        primary_key=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    started_date = Column(BigInteger, nullable=False)
    lead = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))
    completed_questions = Column(BigInteger, default=0)
    correct_questions = Column(BigInteger, default=0)
    session = relationship("SessionModel", back_populates="session_question", uselist=False)
    question = relationship("QuestionModel", uselist=False, viewonly=True)
    tg_users = relationship("TgUsersModel", back_populates="sessions", uselist=False)
    response = relationship("AnswerResponseStageModel", back_populates="session", uselist=False)


class AnswerResponseStageModel(db):
    __tablename__ = "response_stage"
    session_id = Column(BigInteger, ForeignKey("sessions_question.session_id", ondelete="CASCADE"), nullable=False,
                        primary_key=True)
    respondent = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))
    tg_user = relationship("TgUsersModel", back_populates="respondent")
    session = relationship("SessionCurrentQuestionModel", back_populates="response")


class LastSessionModel(db):
    __tablename__ = "last_session"
    session_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), nullable=False,
                        primary_key=True)
    lead = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"))
    completed_questions = Column(BigInteger)
    correct_questions = Column(BigInteger)
    session = relationship("SessionModel", back_populates="session_last")
    tg_users = relationship("TgUsersModel", back_populates="last_sessions", uselist=False)


class TgUserChatModel(db):
    __tablename__ = "tg_user_chat"
    chat_id = Column(BigInteger, ForeignKey("sessions.chat_id", ondelete="CASCADE"), primary_key=True)
    id = Column(BigInteger, ForeignKey("tg_users.id", ondelete="CASCADE"), primary_key=True)
    tg_user = relationship("TgUsersModel", back_populates="chat")
    sessions = relationship("SessionModel", back_populates="tg_users")


class TgUsersModel(db):
    __tablename__ = "tg_users"
    id = Column(BigInteger, primary_key=True)
    uname = Column(VARCHAR(256), index=True)
    chat = relationship("TgUserChatModel", back_populates="tg_user")
    sessions = relationship("SessionCurrentQuestionModel", back_populates="tg_users")
    respondent = relationship("AnswerResponseStageModel", back_populates="tg_user")
    last_sessions = relationship("LastSessionModel", back_populates="tg_users")
