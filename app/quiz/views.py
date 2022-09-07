from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound, HTTPUnprocessableEntity, HTTPBadRequest
from aiohttp_apispec import querystring_schema, request_schema, response_schema
from sqlalchemy.exc import IntegrityError

from app.quiz.models import Answer
from app.quiz.schemes import (
    ListQuestionSchema,
    QuestionSchema,
    ThemeIdSchema,
    ThemeListSchema,
    ThemeSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class ThemeAddView(AuthRequiredMixin, View):
    @request_schema(ThemeSchema)
    @response_schema(ThemeSchema)
    async def post(self):
        title = self.data["title"]
        theme = ""
        try:
            theme = await self.store.quizzes.create_theme(title=title)
        except IntegrityError as e:
            match e.orig.pgcode:
                case '23503':
                    raise HTTPNotFound
                case "23505":
                    raise HTTPConflict
        return json_response(data=ThemeSchema().dump(theme))


class ThemeListView(AuthRequiredMixin, View):
    @response_schema(ThemeListSchema)
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        return json_response(
            data=ThemeListSchema().dump({"themes": themes})
        )


class QuestionAddView(AuthRequiredMixin, View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        answers_ = self.data["answers"]
        title_ = self.data["title"]
        theme_id_ = self.data["theme_id"]
        if len(answers_) <= 1:
            raise HTTPBadRequest
        cnt = 0
        for i in answers_:
            if i["is_correct"]:
                cnt += 1
        if cnt != 1:
            raise HTTPBadRequest
        if await self.store.quizzes.get_question_by_title(title_):
            raise HTTPConflict

        try:
            question = await self.store.quizzes.create_question(
                title=title_,
                theme_id=theme_id_,
                answers=[Answer(title=anwser["title"], is_correct=anwser["is_correct"]) for anwser in answers_]
            )
        except IntegrityError as e:
            if e.orig.pgcode == '23503':
                raise HTTPNotFound
        return json_response(data=QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @querystring_schema(ThemeIdSchema)
    @response_schema(ListQuestionSchema)
    async def get(self):
        if "theme_id" not in self.request.query:
            raw_res = await self.store.quizzes.list_questions()
        else:
            raw_res = await self.store.quizzes.list_questions(int(self.request.query["theme_id"]))
        return json_response(
            data=ListQuestionSchema().dump(
                {"questions": raw_res}
            )
        )
        # return json_response(data={
        #     "questions": res
        # })
        # raise NotImplemented
