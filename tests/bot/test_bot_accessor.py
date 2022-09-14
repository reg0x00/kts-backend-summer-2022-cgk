import logging

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.bot.models import SessionModel, SessionCurrentQuestionModel, TgUsersModel, \
    AnswerResponseStageModel
from app.bot.models_dc import User, BotSession
from app.quiz.models import Question
from tests.utils import check_empty_table_exists
from app.store import Store
import time


class TestBotStore:
    async def test_table_exists(self, cli):
        await check_empty_table_exists(cli, "sessions")
        await check_empty_table_exists(cli, "sessions_question")
        await check_empty_table_exists(cli, "response_stage")
        await check_empty_table_exists(cli, "last_session")
        await check_empty_table_exists(cli, "tg_users")

    async def test_random_user_select(self, cli, session_1: BotSession, user_chat_1: User, user_chat_2: User,
                                      user_chat_3: User,
                                      store: Store):
        unique = set()
        for _ in range(10):
            unique.add((await store.bot_sessions.get_random_user(chat_id=session_1.chat_id)).id)
        assert len(unique) > 1

    async def test_random_user_select_empty(self, cli, store: Store):
        with pytest.raises(FileNotFoundError) as exc_info:
            await store.bot_sessions.get_random_user(chat_id=1)
        assert exc_info.value.args[0] == "User not found"

    async def test_random_question_select(self, cli, question_1: Question, question_2: Question, question_3: Question,
                                          store: Store):
        unique = set()
        for _ in range(10):
            unique.add((await store.bot_sessions.get_random_question()).id)
        assert len(unique) > 1

    async def test_start_session(self, cli, question_1: Question, question_2: Question, question_3: Question,
                                 session_1: BotSession,
                                 user_chat_1: User,
                                 store: Store):
        chat_id = session_1.chat_id
        start = int(time.time())
        res1 = await store.bot_sessions.start_session(chat_id=chat_id, started_date=start)
        with pytest.raises(IntegrityError) as exc_info:
            await store.bot_sessions.start_session(chat_id=chat_id, started_date=start)
        assert exc_info.value.orig.pgcode == "23505"
        res = await store.bot_sessions.get_running_session(chat_id=chat_id)
        assert res == res1


    async def test_add_user(self, cli, store: Store, session_1: BotSession):
        user_orig = User(id=123, chat_id=[session_1.chat_id], uname="asd")
        await store.bot_sessions.create_user(user_orig)
        async with cli.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == user_orig.id).options(joinedload(TgUsersModel.chat))
            user_db = (await (session.execute(q))).scalars().first()
            res_db = User(chat_id=[i.chat_id for i in user_db.chat], uname=user_db.uname, id=user_db.id)
        assert res_db == user_orig

    async def test_add_user_multiple_chats(self, cli, store: Store, session_1: BotSession, session_2: BotSession):
        user_orig = User(id=123, chat_id=[session_1.chat_id], uname="asd")
        await store.bot_sessions.create_user(user_orig)
        async with cli.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == user_orig.id).options(joinedload(TgUsersModel.chat))
            user_db = (await (session.execute(q))).scalars().first()
            res_db = User(chat_id=[i.chat_id for i in user_db.chat], uname=user_db.uname, id=user_db.id)
        assert res_db == user_orig
        user_orig.chat_id.append(session_2.chat_id)
        await store.bot_sessions.create_user(user_orig)
        async with cli.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == user_orig.id).options(joinedload(TgUsersModel.chat))
            user_db = (await (session.execute(q))).scalars().first()
            res_db = User(chat_id=[i.chat_id for i in user_db.chat], uname=user_db.uname, id=user_db.id)
        assert res_db == user_orig

    async def test_alter_respondent(self, cli, question_1: Question, question_2: Question, question_3: Question,
                                    session_1: BotSession,
                                    user_chat_1: User,
                                    user_chat_2: User,
                                    store: Store):
        chat_id = session_1.chat_id
        res1 = await store.bot_sessions.set_respondent(respondent=user_chat_1.id, session_id=chat_id)
        assert res1 == user_chat_1
        async with cli.app.database.session() as session:
            async with session.begin():
                q = select(AnswerResponseStageModel).where(AnswerResponseStageModel.session_id == session_1.chat_id)
                assert user_chat_1.id == (await (session.execute(q))).scalars().first().respondent
        res2 = await store.bot_sessions.set_respondent(respondent=user_chat_2.id, session_id=chat_id)
        assert res2 == user_chat_2
        async with cli.app.database.session() as session:
            async with session.begin():
                q = select(AnswerResponseStageModel).where(AnswerResponseStageModel.session_id == session_1.chat_id)
                assert user_chat_2.id == (await (session.execute(q))).scalars().first().respondent
