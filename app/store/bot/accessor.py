import typing

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import joinedload

from app.base.base_accessor import BaseAccessor
from app.bot.models import BotSession, SessionModel, SessionCurrentQuestionModel, TgUsersModel, SessionQuestion, User, \
    LastSession, LastSessionModel, AnswerResponseStageModel, TgChatUsersModel, UserChat
from app.quiz.models import QuestionModel, Question, Answer

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotAccessor(BaseAccessor):
    async def connect(self, app: "Application"):
        # TODO Restore sessions
        ...

    async def disconnect(self, app: "Application"):
        ...

    async def get_random_question(self) -> Question:
        async with self.app.database.session() as session:
            q = select(QuestionModel).order_by(func.random()).limit(1).options(joinedload(QuestionModel.answers))
            question = (await session.execute(q)).scalars().first()
        if not question:
            raise FileNotFoundError("Question not found")
        return Question(id=question.id, title=question.title, answers=[Answer(title=i.title) for i in question.answers])

    async def get_random_user(self, chat_id: int) -> User:
        async with self.app.database.session() as session:
            q = select(TgChatUsersModel).where(TgChatUsersModel.chat_id == chat_id).order_by(func.random()).limit(
                1).options(joinedload(TgChatUsersModel.tg_user))
            user = (await session.execute(q)).scalars().first()
        if not user:
            raise FileNotFoundError("User not found")
        return User(user.id, uname=user.tg_user.uname)

    async def create_user(self, user_id: int | None = None, uname: str | None = None) -> User:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(TgUsersModel).where(TgUsersModel.id == user_id)
                res = (await (session.execute(q))).scalars().first()
                if not res:
                    res = TgUsersModel(id=user_id, uname=uname)
                    session.add(res)
        return User(id=res.id, uname=res.uname)

    async def add_user_chat(self, user_id: int, chat_id: int, uname: str | None = None) -> UserChat:
        await self.create_session(chat_id)
        await self.create_user(user_id, uname=uname)
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(TgChatUsersModel).where(
                    (TgChatUsersModel.id == user_id) & (TgChatUsersModel.chat_id == chat_id))
                res = (await (session.execute(q))).scalars().first()
                if not res:
                    res = TgChatUsersModel(id=user_id, chat_id=chat_id)
                    session.add(res)
        return UserChat(id=res.id, chat_id=res.chat_id, uname=uname)

    async def create_session(self, chat_id: int) -> BotSession:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(SessionModel).where(SessionModel.chat_id == chat_id)
                res = (await (session.execute(q))).scalars().first()
                if not res:
                    res = SessionModel(chat_id=chat_id)
                    session.add(res)

        return BotSession(chat_id=res.chat_id)

    async def start_session(self, chat_id: int, started_date: int) -> BotSession:
        session_table = await self.create_session(chat_id)
        question = await self.get_random_question()
        lead = await self.get_random_user(chat_id=chat_id)
        async with self.app.database.session() as session:
            async with session.begin():
                new_session = SessionCurrentQuestionModel(
                    question_id=question.id,
                    started_date=started_date,
                    lead=lead.id,
                    session_id=session_table.chat_id
                )
                session.add(new_session)
        return BotSession(
            chat_id=chat_id,
            session_question=
            SessionQuestion(
                question=question,
                started_date=new_session.started_date,
                completed_questions=new_session.completed_questions,
                correct_questions=new_session.correct_questions,
                lead=User(lead.id, uname=lead.uname)
            ))

    async def get_running_session(self, chat_id: int) -> BotSession:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(SessionModel).where(SessionModel.chat_id == chat_id).options(
                    joinedload(SessionModel.session_question))
                running_session = (await session.execute(q)).scalars().first().session_question
                running_session = select(SessionCurrentQuestionModel).where(
                    SessionCurrentQuestionModel.session_id == running_session.session_id).options(
                    joinedload(SessionCurrentQuestionModel.question))
                running_session = (await session.execute(running_session)).scalars().first()
                q = select(TgUsersModel).where(TgUsersModel.id == running_session.lead)
                lead_uname = (await session.execute(q)).scalars().first().uname

        return BotSession(
            chat_id=chat_id,
            session_question=
            SessionQuestion(
                question=(await self.app.store.quizzes.get_question_by_title(running_session.question.title)),
                started_date=running_session.started_date,
                completed_questions=running_session.completed_questions,
                correct_questions=running_session.correct_questions,
                lead=User(id=running_session.lead, uname=lead_uname)
            ))

    async def set_respondent(self, respondent: int, session_id: int) -> User:
        async with self.app.database.session() as session:
            async with session.begin():
                if not (await (session.execute(
                        select(AnswerResponseStageModel).where(
                            AnswerResponseStageModel.session_id == session_id)))).scalars().first():
                    q = AnswerResponseStageModel(
                        session_id=session_id,
                        respondent=respondent
                    )
                    session.add(q)
                else:
                    q = update(AnswerResponseStageModel).where(
                        AnswerResponseStageModel.session_id == session_id).values(respondent=respondent)
                    await session.execute(q)

    # async def get_last_session(self, chat_id: int) -> LastSession:

    async def stop_session(self, chat_id: int) -> LastSession:
        async with self.app.database.session() as session:
            async with session.begin():
                active_session = await self.get_running_session(chat_id=chat_id)
                q = delete(SessionModel).where(SessionModel.chat_id == chat_id)
                await session.execute(q)
                session_table = await self.create_session(chat_id)
                to_last_session = LastSessionModel(
                    session_id=session_table.chat_id,
                    lead=active_session.lead,
                    completed_questions=active_session.completed_questions,
                    correct_questions=active_session.correct_questions
                )
                session.add(to_last_session)
        return LastSession(
            lead=to_last_session.lead,
            correct_questions=to_last_session.correct_questions,
            completed_questions=to_last_session.completed_questions
        )
