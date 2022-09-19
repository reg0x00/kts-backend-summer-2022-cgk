import typing
from dataclasses import dataclass
import os

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application

TG_TOKEN_ENV = "TG_TOKEN"
PG_HOST_ENV = "PG_HOST"
MQ_HOST_ENV = "MQ_HOST"


@dataclass
class SessionConfig:
    key: str


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class Commands:
    start: str
    stop: str
    info: str
    add_selection: str
    assign: str
    answer: str


@dataclass
class BotConfig:
    token: str
    discussion_timeout: int
    api: str
    commands: Commands


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "project"


@dataclass
class MqConfig:
    host: str = "127.0.0.1"


@dataclass
class Config:
    admin: AdminConfig
    session: SessionConfig = None
    bot: BotConfig = None
    database: DatabaseConfig = None
    mq: MqConfig = None


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    commands = dict()
    for c in raw_config["bot"]["commands"]:
        commands[c] = "/" + raw_config["bot"]["commands"][c]
    app.config = Config(
        session=SessionConfig(
            key=raw_config["session"]["key"],
        ),
        admin=AdminConfig(
            email=raw_config["admin"]["email"],
            password=raw_config["admin"]["password"],
        ),
        bot=BotConfig(
            token=raw_config["bot"]["tg_token"],
            discussion_timeout=raw_config["bot"]["discussion_timeout"],
            api=raw_config["bot"]["api_path"],
            # commands=Commands(**dict(map(lambda x: (x[0], "/" + x[1]), raw_config["bot"]["commands"].items())))
            commands=Commands(**commands)

        ),
        database=DatabaseConfig(**raw_config["database"]),
        mq=MqConfig(raw_config["mq"]["host"])
    )
    if TG_TOKEN_ENV in os.environ:
        app.config.bot.token = os.getenv(TG_TOKEN_ENV)
    if PG_HOST_ENV in os.environ:
        app.config.database.host = os.getenv(PG_HOST_ENV)
    if MQ_HOST_ENV in os.environ:
        app.config.mq.host = os.getenv(MQ_HOST_ENV)
