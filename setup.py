from setuptools import setup, find_packages
from pkg_resources import parse_requirements


def load_requirements(fname: str) -> list:
    requirements = []
    with open(fname, "r") as fp:
        for req in parse_requirements(fp.read()):
            extras = "[{}]".format(",".join(req.extras)) if req.extras else ""
            requirements.append("{}{}{}".format(req.name, extras, req.specifier))
    return requirements


module_name = "app"

setup(
    name=module_name,
    version="0.0.1",
    author="reg0x00",
    author_email="yurvoyt@gmail.com",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    install_requires=load_requirements("requirements.txt"),
    entry_points={
        "console_scripts": [
            "app-bot = app.bot_ep:main",
            "app-db = app.db_ep:main",
        ]
    },
    include_package_data=True,
)
