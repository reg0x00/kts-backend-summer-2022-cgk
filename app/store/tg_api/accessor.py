import logging
import typing
import asyncio

from aiohttp import TCPConnector
from aiohttp.client import ClientSession
from aio_pika.patterns import Master

from app.base.base_accessor import BaseAccessor
from app.bot.models_dc import User
from app.store.tg_api.dataclasses import Message, Update, UpdateMessage
from app.store.tg_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application


class TgApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", listen: bool = False, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.listen = listen
        self.session: ClientSession | None = None
        self.token: str | None = None
        self.poller: Poller | None = None
        self.offset: int | None = None

    async def connect(self, app: "Application"):
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False))
        if not self.listen:
            return
        try:
            await self._get_long_poll_service()
        except Exception as e:
            self.logger.error("Exception", exc_info=e)
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        await self.poller.start()

    async def disconnect(self, app: "Application"):
        if self.session:
            await self.session.close()
        if self.poller:
            await self.poller.stop()

    @staticmethod
    def _build_query(host: str, token: str, method: str, params: dict) -> str:
        url = host + token + "/" + method + "?"
        url += "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    async def response_error(self, data):
        logging.error(data)
        await asyncio.sleep(1)

    async def _get_long_poll_service(self):
        async with self.session.get(
                self._build_query(
                    host=self.app.config.bot.api,
                    method="getUpdates",
                    params={},
                    token=self.app.config.bot.token
                )
        ) as resp:
            data = (await resp.json())
            if not data["ok"]:
                await self.response_error(data)
            self.logger.info(data)
            self.offset = (max([m["update_id"] for m in data["result"]]) + 1) if data["result"] else 0

    async def poll(self):
        async with self.session.get(
                self._build_query(
                    host=self.app.config.bot.api,
                    method="getUpdates",
                    params={
                        "offset": self.offset,
                        "timeout": 5,
                    },
                    token=self.app.config.bot.token
                )
        ) as resp:
            data = await resp.json()
            if not data["ok"]:
                await self.response_error(data)
                return
            self.logger.info(data)
            if not data["result"]:
                return
            self.offset = max(m["update_id"] for m in data["result"]) + 1
            raw_updates = data.get("result", [])
            updates = []
            for update in raw_updates:
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    updates.append(
                        Update(
                            update_id=update["update_id"],
                            object=UpdateMessage(
                                date=msg["date"],
                                from_id=msg["from"]["id"],
                                from_username=msg["from"]["username"],
                                chat_id=msg["chat"]["id"],
                                text=msg["text"],
                                is_command="entities" in msg and any(
                                    [m["type"] == "bot_command" for m in msg["entities"]]),
                                is_mention="entities" in msg and any([m["type"] == "mention" for m in msg["entities"]]),
                            ),
                        )
                    )
            channel = await self.app.mq.mq_connection.channel()
            master = Master(channel)
            for task_id in range(len(updates)):
                await master.proxy.my_task_name(update=updates[task_id])
            # await self.app.store.bots_manager.handle_updates(updates)

    async def send_message(self, message: Message) -> None:
        async with self.session.get(
                self._build_query(
                    host=self.app.config.bot.api,
                    method="sendMessage",
                    params={
                        "chat_id": message.user_id,
                        "text": message.text,
                    },
                    token=self.app.config.bot.token
                )
        ) as resp:
            data = await resp.json()
            self.logger.info(data)
