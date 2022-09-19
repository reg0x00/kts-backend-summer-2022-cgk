import os
from pathlib import Path

from app.web.tg_api_app import setup_app
from aiohttp.web import run_app


def main():
    run_app(
        setup_app(
            config_path=str(Path(os.path.realpath(__file__)).parent.parent / "config.yml")
        )
        , port=1232
    )


if __name__ == "__main__":
    main()
