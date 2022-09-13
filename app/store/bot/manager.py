import logging
import typing
from logging import getLogger
import time
import asyncio

from sqlalchemy.exc import IntegrityError

from app.store.tg_api.dataclasses import Message, Update
from app.bot.models import BotSession

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        self.sessions: dict[int] = dict()

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            if not update.object.is_command:  # if message is not command, then reply
                await self.app.store.tg_api.send_message(
                    Message(
                        user_id=update.object.from_id,
                        text="Привет!",
                    )
                )
            else:
                send_id = update.object.chat_id
                match update.object.text:
                    case "/start":
                        await self.create_session(chat_id=send_id, started_date=update.object.date)
                    case "/assign":
                        if not update.object.is_mention:
                            await self.app.store.tg_api.send_message(
                                Message(
                                    user_id=send_id,
                                    text="укажите пользователя",
                                )
                            )
                        else:
                            sess = await self.app.store.bot_sessions.get_running_session(chat_id=send_id)
                            await self.set_respondent(update.object.text.split()[-1][1:], session_id=sess.chat_id)
                            await self.app.store.tg_api.send_message(
                                Message(
                                    user_id=send_id,
                                    text="Отвечает пользователь: ",
                                )
                            )

    async def create_session(self, chat_id: int, started_date: int):
        admins = await self.app.store.tg_api.get_admins(chat_id=chat_id)
        for a in admins:
            await self.app.store.bot_sessions.add_user_chat(chat_id=chat_id, user_id=a.id, uname=a.uname)
        try:
            bt_session = await self.app.store.bot_sessions.start_session(chat_id, started_date=started_date)
        except IntegrityError as e:
            match e.orig.pgcode:
                case "23505":
                    bt_session = await self.app.store.bot_sessions.get_running_session(chat_id)
                    await self.app.store.tg_api.send_message(
                        Message(
                            user_id=chat_id,
                            text=f"Сессия уже начата, вопрос: {bt_session.session_question.question.title}, капитан: {bt_session.session_question.lead.uname}",
                        )
                    )
                    if time.time() > bt_session.session_question.started_date + self.app.config.bot.discussion_timeout:
                        await self.app.store.tg_api.send_message(
                            Message(
                                user_id=bt_session.chat_id,
                                text="Выберите отвечающего",
                            )
                        )
                    return
            raise e
        except FileNotFoundError as e:
            await self.app.store.tg_api.send_message(
                Message(
                    user_id=chat_id,
                    text=e.args[0],
                )
            )
            return
        except Exception as e:
            logging.warning(e)
            raise e
        await self.app.store.tg_api.send_message(
            Message(
                user_id=chat_id,
                text=f"Сессия начата, вопрос: {bt_session.session_question.question.title}, капитан: {bt_session.session_question.lead.uname}",
            )
        )
        await self.start_session_runner(bt_session)

    async def start_session_runner(self, bot_session: BotSession):
        event = asyncio.Event()
        task = asyncio.create_task(self.session_runner(bot_session, event))
        self.sessions[bot_session.chat_id] = (task, event)

    async def add_chat_user(self, chat_id: int, user_id: int):
        await self.app.store.bot_sessions.add_user_chat(user_id=user_id, chat_id=chat_id)

    async def set_respondent(self, respondent: str, session_id: int):
        await self.app.store.bot_sessions.set_respondent(respondent=respondent, session_id=session_id)

    async def session_runner(self, bot_session: BotSession, stop_event: asyncio.Event):
        if time.time() > bot_session.session_question.started_date + self.app.config.bot.discussion_timeout:
            return  # if restored from db
        while time.time() < bot_session.session_question.started_date + self.app.config.bot.discussion_timeout and \
                not stop_event.is_set():
            await asyncio.sleep(0.5)
        if stop_event.is_set():
            return
        await self.app.store.tg_api.send_message(
            Message(
                user_id=bot_session.chat_id,
                text="Выберите отвечающего",
            )
        )
