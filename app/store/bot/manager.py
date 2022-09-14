import logging
import typing
from logging import getLogger
import time
import asyncio

from sqlalchemy.exc import IntegrityError

from app.store.tg_api.dataclasses import Message, Update
from app.bot.models_dc import BotSession, User

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        self.sessions_timers: dict[int] = dict()
        self.sessions: dict[int] = dict()

    async def session_not_found(self, chat_id: int):
        await self.app.store.tg_api.send_message(
            Message(
                user_id=chat_id,
                text="Сессия ещё не была начата",
            )
        )

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
                chat_id = update.object.chat_id
                if chat_id not in self.sessions:
                    await self.app.store.bot_sessions.create_session(chat_id)
                    self.sessions[chat_id] = BotSession(chat_id=chat_id)
                match update.object.text.split()[0]:
                    case self.app.config.bot.commands.start:
                        await self.create_session(chat_id=chat_id, started_date=update.object.date)
                    case self.app.config.bot.commands.assign:
                        if not update.object.is_mention:
                            await self.app.store.tg_api.send_message(
                                Message(
                                    user_id=chat_id,
                                    text="Укажите пользователя с помощью @",
                                )
                            )
                        else:
                            if chat_id not in self.sessions or self.sessions[chat_id].session_question is None:
                                await self.session_not_found(chat_id)
                                return
                            sess = self.sessions[chat_id]
                            if update.object.from_id != sess.session_question.lead.id:
                                await self.app.store.tg_api.send_message(Message(
                                    user_id=chat_id,
                                    text=f"Назначать отвечающего может только капитан {sess.session_question.lead.uname}",
                                ))
                            else:
                                in_uname = update.object.text.split()[-1][1:]
                                selected_user = await self.app.store.bot_sessions.get_user_by_uname(in_uname)
                                if not selected_user:
                                    await self.app.store.tg_api.send_message(
                                        Message(
                                            user_id=chat_id,
                                            text=f"Пользователь {in_uname} не участвует в игре",
                                        ))
                                    return
                                await self.set_respondent(selected_user.id, session_id=sess.chat_id)
                                self.sessions[chat_id].session_question.respondent = in_uname
                                await self.app.store.tg_api.send_message(
                                    Message(
                                        user_id=chat_id,
                                        text=f"Отвечает пользователь: {in_uname}",
                                    )
                                )
                    case self.app.config.bot.commands.add_selection:
                        await self.app.store.bot_sessions.create_user(User(
                            id=update.object.from_id,
                            uname=update.object.from_username,
                            chat_id=[update.object.chat_id]
                        ))
                        await self.set_respondent(update.object.from_id, update.object.chat_id)
                        await self.app.store.tg_api.send_message(
                            Message(
                                user_id=chat_id,
                                text=f"Пользователь {update.object.from_username} участвует в игре",
                            )
                        )

    async def create_session(self, chat_id: int, started_date: int):
        # admins = await self.app.store.tg_api.get_admins(chat_id=chat_id)
        # for a in admins:
        #     await self.app.store.bot_sessions.create_user(User(uname=a.uname, chat_id=a.chat_id, id=a.id))
        try:
            bt_session = await self.app.store.bot_sessions.start_session(chat_id, started_date=started_date)
        except IntegrityError as e:
            match e.orig.pgcode:
                case "23505":
                    await self.app.store.tg_api.send_message(
                        Message(
                            user_id=chat_id,
                            text=f"Сессия уже начата, вопрос: {self.sessions[chat_id].session_question.question.title}, капитан: {self.sessions[chat_id].session_question.lead.uname}",
                        )
                    )
                    if self.sessions[chat_id].session_question.respondent:
                        await self.app.store.tg_api.send_message(
                            Message(
                                user_id=chat_id,
                                text=f"Отвечает пользователь: {self.sessions[chat_id].session_question.respondent}",
                            )
                        )
                    elif time.time() > self.sessions[
                        chat_id].session_question.started_date + self.app.config.bot.discussion_timeout:
                        await self.app.store.tg_api.send_message(
                            Message(
                                user_id=self.sessions[chat_id].chat_id,
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
        self.sessions[bot_session.chat_id] = bot_session
        self.sessions_timers[bot_session.chat_id] = (task, event)

    async def set_respondent(self, respondent: int, session_id: int):
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
