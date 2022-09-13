import logging

import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.bot.models import User, SessionModel, SessionCurrentQuestionModel, TgUsersModel, TgChatUsersModel, UserChat, \
    BotSession, AnswerResponseStageModel
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
        await check_empty_table_exists(cli, "tg_chat_users")

    async def test_random_user_select(self, cli, session_1: BotSession, user_chat_1: UserChat, user_chat_2: UserChat,
                                      user_chat_3: UserChat,
                                      store: Store):
        unique = set()
        for _ in range(10):
            unique.add((await store.bot_sessions.get_random_user(chat_id=session_1.chat_id)).id)
        assert len(unique) > 1

    async def test_random_user_select_get_uname(self, cli, store: Store, session_1: BotSession, user_chat_1: UserChat):
        user = await store.bot_sessions.get_random_user(chat_id=user_chat_1.chat_id)
        assert user == User(uname=user_chat_1.uname, id=user_chat_1.id)

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
                                 user_chat_1: UserChat,
                                 store: Store):
        chat_id = session_1.chat_id
        start = int(time.time())
        res1 = await store.bot_sessions.start_session(chat_id=chat_id, started_date=start)
        res = await store.bot_sessions.get_running_session(chat_id=chat_id)
        assert res == res1

    async def test_add_user(self, cli, store: Store):
        user_id = 432
        user = await store.bot_sessions.create_user(user_id)
        async with cli.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == user_id)
            user_db = (await (session.execute(q))).scalars().first()
        assert user_db.id == user.id

    async def test_add_user_uname(self, cli, store: Store):
        user_id = 432
        uname = "User"
        user = await store.bot_sessions.create_user(user_id, uname=uname)
        async with cli.app.database.session() as session:
            q = select(TgUsersModel).where(TgUsersModel.id == user_id)
            user_db = (await (session.execute(q))).scalars().first()
        assert user_db.id == user.id

    async def test_add_user_group(self, cli, store: Store):
        chat_id = 100
        user_id = 200
        await store.bot_sessions.create_session(chat_id)
        await store.bot_sessions.create_user(user_id)
        user_chat = await store.bot_sessions.add_user_chat(user_id, chat_id)
        async with cli.app.database.session() as session:
            q = select(TgChatUsersModel).where(TgChatUsersModel.id == user_id)
            chat_user_db = (await (session.execute(q))).scalars().first()
        user_chat_db = UserChat(id=chat_user_db.id, chat_id=chat_user_db.chat_id)
        assert user_chat_db == user_chat

    async def test_alter_respondent(self, cli, question_1: Question, question_2: Question, question_3: Question,
                                    session_1: BotSession,
                                    user_chat_1: UserChat,
                                    user_chat_2: UserChat,
                                    store: Store):
        chat_id = session_1.chat_id
        await store.bot_sessions.set_respondent(respondent=user_chat_1.id, session_id=chat_id)
        async with cli.app.database.session() as session:
            async with session.begin():
                q = select(AnswerResponseStageModel).where(AnswerResponseStageModel.session_id == session_1.chat_id)
                assert user_chat_1.id == (await (session.execute(q))).scalars().first().respondent
        await store.bot_sessions.set_respondent(respondent=user_chat_2.id, session_id=chat_id)
        async with cli.app.database.session() as session:
            async with session.begin():
                q = select(AnswerResponseStageModel).where(AnswerResponseStageModel.session_id == session_1.chat_id)
                assert user_chat_2.id == (await (session.execute(q))).scalars().first().respondent
