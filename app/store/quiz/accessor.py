from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from app.base.base_accessor import BaseAccessor
from app.quiz.models import QuestionModel, AnswerModel
from app.quiz.models import (
    Answer,
    Question
)


class QuizAccessor(BaseAccessor):
    async def create_answers(
            self, question_id: int, answers: list[Answer]
    ) -> list[Answer]:
        insert_blk = []
        for i in answers:
            insert_blk.append(AnswerModel(question_id=question_id, title=i.title))
        async with self.app.database.session() as session:
            async with session.begin():
                session.add_all(insert_blk)
        return answers

    async def create_question(
            self, title: str, answers: list[Answer]
    ) -> Question:
        now_question = QuestionModel(title=title,
                                     answers=[
                                         AnswerModel(**ans.__dict__)
                                         for ans in answers
                                     ])
        async with self.app.database.session() as session:
            async with session.begin():
                session.add(now_question)
        question = Question(id=now_question.id, title=title, answers=answers.copy())
        return question

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        async with self.app.database.session() as session:
            q = select(QuestionModel).where(QuestionModel.title == title).options(
                joinedload(QuestionModel.answers))
            question = (await session.execute(q)).scalar()
            if not question:
                return None
        answer_res = []
        for row in question.answers:
            answer_res.append(Answer(title=row.title))
        return Question(id=question.id, title=question.title, answers=answer_res)

    async def list_questions(self) -> list[Question]:
        async with self.app.database.session() as session:
            q = select(QuestionModel).options(joinedload(QuestionModel.answers))
            questions = await session.execute(q)
        res = []
        for question in questions.scalars().unique():
            tmp_anws = []
            for anws in question.answers:
                tmp_anws.append(Answer(title=anws.title))
            res.append(Question(id=question.id, title=question.title, answers=tmp_anws))
        return res
