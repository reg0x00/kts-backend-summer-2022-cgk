import datetime
import logging

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.bot.models import SessionModel, SessionCurrentQuestionModel, TgUsersModel, \
    AnswerResponseStageModel
from app.bot.models_dc import User, BotSession, LastSession
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
        res_start = await store.bot_sessions.start_session(chat_id=chat_id, started_date=start)
        with pytest.raises(IntegrityError) as exc_info:
            await store.bot_sessions.start_session(chat_id=chat_id, started_date=start)
        assert exc_info.value.orig.pgcode == "23505"
        res_running = await store.bot_sessions.get_running_session(chat_id=chat_id)
        assert res_start.chat_id == chat_id
        assert res_start.session_question.lead == user_chat_1
        assert res_start.session_question.question in [question_1, question_2, question_3]
        assert res_start == res_running

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
        chat_id = user_chat_1.chat_id[0]
        await store.bot_sessions.start_session(chat_id, datetime.datetime.now().timestamp())
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

    async def test_change_score(self, question_1: Question, question_2: Question,
                                question_3: Question,
                                active_session_1: BotSession,
                                user_chat_1: User,
                                user_chat_2: User,
                                store: Store):
        chat_id = user_chat_1.chat_id[0]
        await store.bot_sessions.change_score(change=0, chat_id=active_session_1.chat_id)
        sess_0 = await store.bot_sessions.get_running_session(chat_id=chat_id)
        active_session_1.session_question.completed_questions += 1
        assert sess_0 == active_session_1
        await store.bot_sessions.change_score(change=1, chat_id=active_session_1.chat_id)
        sess_1 = await store.bot_sessions.get_running_session(chat_id=chat_id)
        active_session_1.session_question.completed_questions += 1
        active_session_1.session_question.correct_questions += 1
        assert sess_1 == active_session_1
        await store.bot_sessions.stop_session(chat_id=active_session_1.chat_id)
        with pytest.raises(FileNotFoundError):
            await store.bot_sessions.change_score(change=1, chat_id=active_session_1.chat_id)

    async def test_stop_get_last_session(self, question_1: Question, question_2: Question,
                                         question_3: Question,
                                         active_session_1: BotSession,
                                         user_chat_1: User,
                                         user_chat_2: User,
                                         store: Store):
        session_last = await store.bot_sessions.stop_session(chat_id=active_session_1.chat_id)
        assert session_last.lead == active_session_1.session_question.lead.id

    async def test_upsert_last_session(self, question_1: Question, question_2: Question,
                                       question_3: Question,
                                       active_session_1: BotSession,
                                       user_chat_1: User,
                                       user_chat_2: User,
                                       store: Store):
        await store.bot_sessions.change_score(change=1, chat_id=active_session_1.chat_id)
        await store.bot_sessions.change_score(change=0, chat_id=active_session_1.chat_id)
        session_last = await store.bot_sessions.stop_session(chat_id=active_session_1.chat_id)
        await store.bot_sessions.start_session(active_session_1.chat_id, active_session_1.session_question.started_date)
        gt_last_session = LastSession(
            chat_id=active_session_1.chat_id,
            lead=active_session_1.session_question.lead,
            correct_questions=1,
            completed_questions=2
        )
        assert session_last == gt_last_session
        session_last2 = await store.bot_sessions.get_last_session(active_session_1.chat_id)
        assert session_last2 == gt_last_session

    async def test_restart_session(self, question_1: Question, question_2: Question,
                                   question_3: Question,
                                   session_1: BotSession,
                                   user_chat_1: User,
                                   user_chat_2: User,
                                   store: Store):
        start = datetime.datetime.now()
        chat_id = user_chat_1.chat_id[0]
        session_start = await store.bot_sessions.start_session(chat_id, start.timestamp())
        start1 = int((start + datetime.timedelta(seconds=5)).timestamp())
        await store.bot_sessions.restart_session(chat_id=chat_id, started_date=start1)
        session = await store.bot_sessions.get_running_session(chat_id=chat_id)
        assert session.session_question.started_date == start1
        for _ in range(10):
            await store.bot_sessions.restart_session(chat_id=chat_id, started_date=start1)
            session = await store.bot_sessions.get_running_session(chat_id=chat_id)
            if session.session_question.question != session_start.session_question.question:
                break
        else:
            assert False

    async def test_delete_respondent(self, question_1: Question, question_2: Question,
                                     question_3: Question,
                                     session_1: BotSession,
                                     user_chat_1: User,
                                     user_chat_2: User,
                                     store: Store):
        start = datetime.datetime.now()
        chat_id = user_chat_1.chat_id[0]
        sess = await store.bot_sessions.start_session(chat_id, start.timestamp())
        assert sess.session_question.respondent is None
        await store.bot_sessions.set_respondent(user_chat_2.id, user_chat_2.chat_id[0])
        assert (await store.bot_sessions.get_running_session(chat_id)).session_question.respondent == user_chat_2
        await store.bot_sessions.delete_respondent(user_chat_2.chat_id[0])
        assert (await store.bot_sessions.get_running_session(chat_id)).session_question.respondent is None

    async def test_last_session(self, question_1: Question, question_2: Question,
                                question_3: Question,
                                session_1: BotSession,
                                user_chat_1: User,
                                user_chat_2: User,
                                store: Store):
        start = datetime.datetime.now()
        chat_id = user_chat_1.chat_id[0]
        sess = await store.bot_sessions.start_session(chat_id, start.timestamp())
        last_sess = await store.bot_sessions.get_last_session(chat_id)
        assert last_sess is None
        await store.bot_sessions.change_score(change=1, chat_id=chat_id)
        await store.bot_sessions.change_score(change=0, chat_id=chat_id)
        await store.bot_sessions.stop_session(chat_id=chat_id)
        session_last = await store.bot_sessions.get_last_session(chat_id)
        sess1 = await store.bot_sessions.start_session(user_chat_1.chat_id[0], start.timestamp())
        await store.bot_sessions.change_score(change=1, chat_id=chat_id)
        await store.bot_sessions.change_score(change=1, chat_id=chat_id)
        await store.bot_sessions.stop_session(chat_id=chat_id)
        session_last1 = await store.bot_sessions.get_last_session(chat_id)
        assert session_last.correct_questions == 1
        assert session_last.completed_questions == 2
        assert session_last.lead == sess.session_question.lead
        assert session_last1.completed_questions == 2
        assert session_last1.correct_questions == 2
        assert session_last1.lead == sess1.session_question.lead
        assert session_last.chat_id == chat_id
