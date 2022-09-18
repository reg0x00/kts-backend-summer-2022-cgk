import asyncio
from typing import Optional, TYPE_CHECKING
from aio_pika import connect_robust


if TYPE_CHECKING:
    from app.web.app import Application


class Mq:
    def __init__(self, app: "Application"):
        self.app = app
        self.mq_connection = None
        self.update_worker = None

    async def connect(self, *_: list, **__: dict) -> None:
        self.mq_connection = await connect_robust(f"amqp://guest:guest@{self.app.config.mq.host}/?name=aio-pika%20master")

    async def disconnect(self, *_: list, **__: dict) -> None:
        if self.mq_connection:
            await self.mq_connection.close()

    async def start_worker(self, *_: list, **__: dict) -> None:
        self.update_worker = asyncio.create_task(self.app.store.bots_manager.update_worker())
