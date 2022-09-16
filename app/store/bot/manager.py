import logging
import typing
from logging import getLogger
import time
import asyncio

from sqlalchemy.exc import IntegrityError

from app.store.tg_api.dataclasses import Message, Update
from app.bot.models_dc import BotSession, User, LastSession

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

    async def general_session_info(self, bot_session: BotSession):
        await self.app.store.tg_api.send_message(
            Message(
                user_id=bot_session.chat_id,
                text=f"Раунд {bot_session.session_question.completed_questions}," +
                     f" вопрос: {bot_session.session_question.question.title}, " +
                     f"капитан: {bot_session.session_question.lead.uname}",
            )
        )

    async def last_session_info(self, last_session: LastSession):
        await self.app.store.tg_api.send_message(
            Message(
                user_id=last_session.chat_id,
                text=f"Результаты предыдущей сессии:"
                     f"Счет {last_session.completed_questions}:{last_session.completed_questions},"
                     f"капитан: {last_session.lead.uname}",
            )
        )

    async def start_command(self, update: Update):
        await self.create_session(chat_id=update.object.chat_id, started_date=update.object.date)

    async def info_command(self, update: Update):
        chat_id = update.object.chat_id
        if chat_id not in self.sessions:
            await self.session_not_found(chat_id)
        else:
            session = self.sessions[chat_id]
            if session.session_question:
                await self.general_session_info(session)
            if session.last_session:
                await self.last_session_info(session.last_session)

    async def assign_command(self, update: Update):
        chat_id = update.object.chat_id
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
                self.sessions[chat_id] = await self.app.store.bot_sessions.get_running_session(chat_id=chat_id)
                self.sessions_timers[chat_id][1].set()
                await self.app.store.tg_api.send_message(
                    Message(
                        user_id=chat_id,
                        text=f"Отвечает пользователь: {in_uname}",
                    )
                )

    async def add_selection_command(self, update: Update):
        await self.app.store.bot_sessions.create_user(User(
            id=update.object.from_id,
            uname=update.object.from_username,
            chat_id=[update.object.chat_id]
        ))
        await self.app.store.tg_api.send_message(
            Message(
                user_id=update.object.chat_id,
                text=f"Пользователь {update.object.from_username} участвует в игре",
            )
        )

    async def stop_command(self, update: Update):
        if self.sessions[update.object.chat_id].session_question is None:
            await self.session_not_found(chat_id=update.object.chat_id)
        else:
            last_session = await self.app.store.bot_sessions.stop_session(chat_id=update.object.chat_id)
            await self.add_last_session(last_session)
            await self.app.store.tg_api.send_message(
                Message(
                    user_id=update.object.chat_id,
                    text=f"Сессия закончена. Результат: {last_session.completed_questions}:{last_session.correct_questions}. "
                )
            )

    async def answer_command(self, update: Update):
        session = self.sessions[update.object.chat_id]
        if session and session.session_question and session.session_question.respondent and update.object.from_id == session.session_question.respondent.id:
            if session.check_answer(ans="".join(update.object.text.split()[1:])):
                await self.app.store.bot_sessions.change_score(chat_id=update.object.chat_id, change=0)
                await self.app.store.tg_api.send_message(
                    Message(
                        user_id=update.object.chat_id,
                        text="Ответ правильный",
                    )
                )
            else:
                await self.app.store.bot_sessions.change_score(chat_id=update.object.chat_id, change=0)
                await self.app.store.tg_api.send_message(
                    Message(
                        user_id=update.object.chat_id,
                        text="Ответ неправильный",
                    )
                )
            await self.app.store.bot_sessions.restart_session(chat_id=update.object.chat_id,
                                                              started_date=update.object.date)
            await self.start_session_runner(
                await (self.app.store.bot_sessions.get_running_session(update.object.chat_id)))

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
                if update.object.chat_id not in self.sessions:
                    await self.app.store.bot_sessions.create_session(update.object.chat_id)
                    self.sessions[update.object.chat_id] = BotSession(chat_id=update.object.chat_id)
                match update.object.text.split()[0]:
                    case self.app.config.bot.commands.start:
                        await self.start_command(update)
                    case self.app.config.bot.commands.stop:
                        await self.stop_command(update)
                    case self.app.config.bot.commands.assign:
                        await self.assign_command(update)
                    case self.app.config.bot.commands.add_selection:
                        await self.add_selection_command(update)
                    case self.app.config.bot.commands.answer:
                        await self.answer_command(update)
                    case self.app.config.bot.commands.info:
                        await self.info_command(update)

    async def create_session(self, chat_id: int, started_date: int):
        try:
            bt_session = await self.app.store.bot_sessions.start_session(chat_id, started_date=started_date)
        except IntegrityError as e:
            match e.orig.pgcode:
                case "23505":
                    await self.app.store.tg_api.send_message(
                        Message(
                            user_id=chat_id,
                            text=f"Сессия уже начата, вопрос: " +
                                 f"{self.sessions[chat_id].session_question.question.title}," +
                                 f" капитан: {self.sessions[chat_id].session_question.lead.uname}",
                        )
                    )
                    if self.sessions[chat_id].session_question.respondent:
                        await self.app.store.tg_api.send_message(
                            Message(
                                user_id=chat_id,
                                text=f"Отвечает пользователь: {self.sessions[chat_id].session_question.respondent.uname}",
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
        await self.start_session_runner(bt_session)

    async def add_last_session(self, last_session: LastSession):
        self.sessions[last_session.chat_id].last_session = last_session

    async def start_session_runner(self, bot_session: BotSession, msg: bool = True):
        if msg:
            await self.general_session_info(bot_session)
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
