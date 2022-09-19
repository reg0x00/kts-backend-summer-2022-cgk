import typing

from app.store.database.database import Database
from app.store.database.mq import Mq

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application", tg_listen: bool = False):
        from app.store.bot.manager import BotManager
        from app.store.admin.accessor import AdminAccessor
        from app.store.quiz.accessor import QuizAccessor
        from app.store.tg_api.accessor import TgApiAccessor
        from app.store.bot.accessor import BotAccessor
        if not tg_listen:
            self.quizzes = QuizAccessor(app)
            self.admins = AdminAccessor(app)
            self.bots_manager = BotManager(app)
            self.bot_sessions = BotAccessor(app)
        self.tg_api = TgApiAccessor(app, listen=tg_listen)


def setup_store(app: "Application", tg_listen: bool = False):
    app.mq = Mq(app)
    app.on_startup.append(app.mq.connect)
    app.on_cleanup.append(app.mq.disconnect)
    if not tg_listen:
        app.database = Database(app)
        app.on_startup.append(app.database.connect)
        app.on_cleanup.append(app.database.disconnect)
        app.on_startup.append(app.mq.start_worker)
    app.store = Store(app, tg_listen=tg_listen)
