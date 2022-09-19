import logging

from alembic.config import CommandLine, Config
from pathlib import Path
import os


def main():
    logging.basicConfig(level=logging.DEBUG)
    alembic_cl = CommandLine()
    alembic_cl.parser.add_argument(
        "--pg-url",
        default=os.getenv("APP_PG_URL", "postgresql+asyncpg://kts_user:kts_pass@db/kts"),
        help="Database URL [env var: APP_PG_URL]",
    )
    alembic_args = alembic_cl.parser.parse_args()
    if 'cmd' not in alembic_args:
        alembic_cl.parser.error('too few arguments')
        exit(128)

    # set abs path
    if not os.path.isabs(alembic_args.config):
        alembic_args.config = os.path.join(
            Path(__file__).parent.parent.resolve(), alembic_args.config
        )

    config = Config(
        file_=alembic_args.config, ini_section=alembic_args.name, cmd_opts=alembic_args
    )
    alembic_location = config.get_main_option("script_location")

    # set abs path
    if not os.path.isabs(alembic_location):
        config.set_main_option(
            "script_location",
            os.path.join(Path(__file__).parent.parent.resolve(), alembic_location),
        )
    config.set_main_option("sqlalchemy.url", alembic_args.pg_url)
    exit(alembic_cl.run_cmd(config, alembic_args))


if __name__ == "__main__":
    main()
