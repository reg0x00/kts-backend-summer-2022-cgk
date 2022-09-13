from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound, HTTPUnprocessableEntity, HTTPBadRequest
from aiohttp_apispec import querystring_schema, request_schema, response_schema
from sqlalchemy.exc import IntegrityError

from app.quiz.models import Answer
from app.quiz.schemes import (
    QuestionSchema,
    ListQuestionSchema
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class QuestionAddView(AuthRequiredMixin, View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        answers_ = self.data["answers"]
        title_ = self.data["title"]
        if len(answers_) == 0:
            raise HTTPBadRequest
        if await self.store.quizzes.get_question_by_title(title_):
            raise HTTPConflict

        try:
            question = await self.store.quizzes.create_question(
                title=title_,
                answers=[Answer(**anwser) for anwser in answers_]
            )
        except IntegrityError as e:
            match e.orig.pgcode:
                case '23503':
                    raise HTTPNotFound
                case "23505":
                    raise HTTPConflict
            raise e
        return json_response(data=QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @response_schema(ListQuestionSchema)
    async def get(self):
        raw_res = await self.store.quizzes.list_questions()
        res = QuestionSchema().dump(raw_res, many=True)
        return json_response(data={
            "questions": res
        })
