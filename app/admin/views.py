from aiohttp.web import HTTPForbidden, HTTPUnauthorized
from aiohttp_apispec import request_schema, response_schema
from aiohttp_session import new_session

from app.admin.schemes import AdminSchema
from app.web.app import View
from app.web.utils import json_response


class AdminLoginView(View):
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        admin_data = await self.store.admins.get_by_email(self.data["email"])
        if not admin_data or not admin_data.is_password_valid(self.data["password"]):
            raise HTTPForbidden
        sess = await new_session(self.request)
        admin_data = AdminSchema().dump(admin_data)
        sess["admin"] = admin_data
        return json_response(data=admin_data)


class AdminCurrentView(View):
    @response_schema(AdminSchema, 200)
    async def get(self):
        return json_response(AdminSchema().dump(self.request.admin))
