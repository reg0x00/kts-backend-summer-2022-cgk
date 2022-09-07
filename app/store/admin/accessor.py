import typing

from sqlalchemy import select
from app.admin.models import Admin, AdminModel
from app.base.base_accessor import BaseAccessor
from hashlib import sha256

if typing.TYPE_CHECKING:
    from app.web.app import Application


class AdminAccessor(BaseAccessor):
    async def get_by_email(self, email: str) -> typing.Optional[Admin]:
        async with self.app.database.session() as session:
            q = select(AdminModel).where(AdminModel.email == email)
            res = (await session.execute(q)).all()
            if not res:
                return None
            res = res[0][0]
        return Admin(id=res.id, email=res.email, password=res.password)

    async def create_admin(self, email: str, password: str) -> Admin:
        raise NotImplemented

    async def add_def_admin(self, *_: list, **__: dict):
        async with self.app.database.session() as session:
            async with session.begin():
                new_admin = AdminModel(id=1, email=self.app.config.admin.email,
                                       password=sha256(self.app.config.admin.password.encode()).hexdigest())
                session.add(new_admin)
