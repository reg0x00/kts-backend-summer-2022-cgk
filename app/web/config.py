import typing
from dataclasses import dataclass

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application


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
class Config:
    admin: AdminConfig
    session: SessionConfig = None
    bot: BotConfig = None
    database: DatabaseConfig = None


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    app.config = Config(
        session=SessionConfig(
            key=raw_config["session"]["key"],
        ),
        admin=AdminConfig(
            email=raw_config["admin"]["email"],
            password=raw_config["admin"]["password"],
        ),
        bot=BotConfig(
            token=raw_config["bot"]["token"],
            discussion_timeout=raw_config["bot"]["discussion_timeout"],
            api=raw_config["bot"]["api_path"],
            commands=Commands(**dict(map(lambda x: (x[0], "/" + x[1]), raw_config["bot"]["commands"].items())))
        ),
        database=DatabaseConfig(**raw_config["database"]),
    )
