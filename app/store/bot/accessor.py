import asyncio
import logging
import typing

from sqlalchemy import select, delete, update, func, and_
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.ext.asyncio import AsyncSession
from app.base.base_accessor import BaseAccessor
from app.bot.models import SessionModel, SessionCurrentQuestionModel, TgUsersModel, LastSessionModel, \
    AnswerResponseStageModel, TgUserChatModel
from app.bot.models_dc import User, LastSession, SessionQuestion, BotSession
from app.quiz.models import QuestionModel, Question, Answer

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotAccessor(BaseAccessor):
    async def connect(self, app: "Application"):
        async with self.app.database.session() as session:
            q = select(SessionCurrentQuestionModel)
            sessions_active = (await session.execute(q)).scalars().all()
            for s in sessions_active:
                running_session = await self.get_running_session(s.session_id)
                await self.app.store.bots_manager.start_session_runner(running_session, msg=False)

    async def disconnect(self, app: "Application"):
        pass

    async def get_random_question(self) -> Question:
        async with self.app.database.session() as session:
            q = select(QuestionModel).order_by(func.random()).limit(1).options(joinedload(QuestionModel.answers))
            question = (await session.execute(q)).scalars().first()
        if not question:
            raise FileNotFoundError("Question not found")
        return Question(id=question.id, title=question.title, answers=[Answer(i.title) for i in question.answers])

    async def get_random_user(self, chat_id: int) -> User:
        async with self.app.database.session() as session:
            q = select(TgUserChatModel).where(TgUserChatModel.chat_id == chat_id).order_by(func.random()).limit(
                1).options(joinedload(TgUserChatModel.tg_user))
            user = (await session.execute(q)).scalars().first()
        if not user:
            raise FileNotFoundError("User not found")
        return User(id=user.tg_user.id, uname=user.tg_user.uname, chat_id=user.chat_id)

    async def create_user(self, user: User) -> User:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(TgUsersModel).where(TgUsersModel.id == user.id).options(joinedload(TgUsersModel.chat))
                q_res = (await (session.execute(q))).scalars().first()
                if not q_res:
                    q_res = TgUsersModel(id=user.id, uname=user.uname,
                                         chat=[TgUserChatModel(chat_id=c) for c in user.chat_id])
                    session.add(q_res)
                else:
                    for chat in user.chat_id:
                        if q_res.chat and chat not in [qc.chat_id for qc in q_res.chat]:
                            q_res.chat.append(TgUserChatModel(chat_id=chat))
        return User(id=q_res.id, uname=q_res.uname, chat_id=[i.chat_id for i in q_res.chat])

    async def _create_session(self, chat_id: int, session: AsyncSession) -> BotSession:
        q = select(SessionModel).where(SessionModel.chat_id == chat_id)
        res = (await (session.execute(q))).scalars().first()
        if not res:
            res = SessionModel(chat_id=chat_id)
            session.add(res)

        return BotSession(chat_id=res.chat_id)

    async def create_session(self, chat_id: int, session: AsyncSession | None = None) -> BotSession:
        if not session:
            async with self.app.database.session() as session:
                async with session.begin():
                    return await self._create_session(chat_id, session)
        else:
            return await self._create_session(chat_id, session)

    async def start_session(self, chat_id: int, started_date: int) -> BotSession:
        async with self.app.database.session() as session:
            async with session.begin():
                session_table = await self.create_session(chat_id, session)
                question, lead = await asyncio.gather(self.get_random_question(),
                                                      self.get_random_user(chat_id=chat_id))
                res = SessionCurrentQuestionModel(
                    question_id=question.id,
                    started_date=started_date,
                    lead=lead.id,
                    session_id=session_table.chat_id
                )
                session.add(res)

        return BotSession(
            chat_id=chat_id,
            session_question=
            SessionQuestion(
                question=question,
                started_date=res.started_date,
                completed_questions=res.completed_questions,
                correct_questions=res.correct_questions,
                lead=User(lead.id, uname=lead.uname, chat_id=[chat_id])
            ))

    async def restart_session(self, chat_id: int, started_date: int):
        async with self.app.database.session() as session:
            async with session.begin():
                question = await self.get_random_question()
                await self.delete_respondent(chat_id=chat_id)
                await session.merge(
                    SessionCurrentQuestionModel(
                        question_id=question.id,
                        started_date=started_date,
                        session_id=chat_id
                    )
                )

    async def get_running_session(self, chat_id: int) -> BotSession | None:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(SessionCurrentQuestionModel).where(SessionCurrentQuestionModel.session_id == chat_id). \
                    options(
                    joinedload(SessionCurrentQuestionModel.question).joinedload(QuestionModel.answers)). \
                    options(joinedload(SessionCurrentQuestionModel.tg_users).joinedload(TgUsersModel.chat)). \
                    options(joinedload(SessionCurrentQuestionModel.response).joinedload(
                    AnswerResponseStageModel.tg_user).joinedload(TgUsersModel.chat))
                res = (await session.execute(q)).scalars().first()
                if not res:
                    return
        return BotSession(
            chat_id=chat_id,
            session_question=
            SessionQuestion(
                question=Question(id=res.question.id, title=res.question.title,
                                  answers=[Answer(a.title) for a in res.question.answers]),
                started_date=res.started_date,
                completed_questions=res.completed_questions,
                correct_questions=res.correct_questions,
                lead=User(id=res.tg_users.id, uname=res.tg_users.uname,
                          chat_id=[c.chat_id for c in res.tg_users.chat]),
                respondent=User(
                    id=res.response.tg_user.id,
                    uname=res.response.tg_user.uname,
                    chat_id=[c.chat_id for c in res.response.tg_user.chat]
                ) if res.response else None
            )
        )

    async def change_score(self, change: int, chat_id: int):
        if not (0 == change or change == 1):
            raise ValueError
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(SessionCurrentQuestionModel).where(SessionCurrentQuestionModel.session_id == chat_id)
                sess_q = (await (session.execute(q))).scalars().first()
                if not sess_q:
                    logging.error("Trying to change score to empty session")
                    raise FileNotFoundError
                sess_q.completed_questions += 1
                sess_q.correct_questions += change

    async def set_respondent(self, respondent: int, session_id: int) -> User:
        async with self.app.database.session() as session:
            async with session.begin():
                q = select(TgUsersModel).where(TgUsersModel.id == respondent).options(
                    joinedload(TgUsersModel.chat))
                user = (await (session.execute(q))).scalars().first()
                await session.merge(AnswerResponseStageModel(
                    session_id=session_id,
                    respondent=respondent
                ))
        return User(id=respondent, uname=user.uname, chat_id=[c.chat_id for c in user.chat])

    async def delete_respondent(self, chat_id: int):
        async with self.app.database.session() as session:
            async with session.begin():
                q = delete(AnswerResponseStageModel).where(AnswerResponseStageModel.session_id == chat_id)
                await (session.execute(q))

    async def get_last_session(self, chat_id: int) -> LastSession | None:
        async with self.app.database.session() as session:
            q = select(LastSessionModel).where(LastSessionModel.session_id == chat_id).options(
                joinedload(LastSessionModel.tg_users).joinedload(TgUsersModel.chat))
            res = (await session.execute(q)).scalars().first()
            if not res:
                return
        return LastSession(
            chat_id=chat_id,
            lead=User(
                id=res.tg_users.id,
                uname=res.tg_users.uname,
                chat_id=[c.chat_id for c in res.tg_users.chat]
            ),
            completed_questions=res.completed_questions,
            correct_questions=res.correct_questions,
        )

    async def stop_session(self, chat_id: int) -> LastSession:
        async with self.app.database.session() as session:
            async with session.begin():
                active_session = await self.get_running_session(chat_id=chat_id)
                q = delete(SessionCurrentQuestionModel).where(SessionCurrentQuestionModel.session_id == chat_id)
                await session.execute(q)
                to_last_session = LastSessionModel(
                    session_id=chat_id,
                    lead=active_session.session_question.lead.id,
                    completed_questions=active_session.session_question.completed_questions,
                    correct_questions=active_session.session_question.correct_questions
                )
                await session.merge(to_last_session)
        return LastSession(
            chat_id=chat_id,
            lead=(await self.get_user(to_last_session.lead)),
            correct_questions=to_last_session.correct_questions,
            completed_questions=to_last_session.completed_questions
        )

    async def get_user_by_uname(self, uname: str) -> User | None:
        async with self.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.uname == uname).options(
                joinedload(TgUsersModel.chat))
            user = (await (session.execute(q))).scalars().first()
            if not user:
                return None
        return User(id=user.id, uname=uname, chat_id=[c.chat_id for c in user.chat])

    async def get_user(self, id_: int) -> User | None:
        async with self.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == id_).options(
                joinedload(TgUsersModel.chat))
            user = (await (session.execute(q))).scalars().first()
            if not user:
                return None
        return User(id=user.id, uname=user.uname, chat_id=[c.chat_id for c in user.chat])
