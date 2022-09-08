import typing
from logging import getLogger

from app.store.tg_api.dataclasses import Message, Update

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            if not update.object.is_command:  # if message is not command, then reply
                await self.app.store.tg_api.send_message(
                    Message(
                        user_id=update.object.from_id,
                        text="Привет!",
                    )
                )

    async def setup_session(self, peer_id: str):
        ...
# TODO init session
