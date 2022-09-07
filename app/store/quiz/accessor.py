from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from app.base.base_accessor import BaseAccessor
from app.quiz.models import QuestionModel, ThemeModel, AnswerModel
from app.quiz.models import (
    Answer,
    Question,
    Theme,
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        new_theme_model = ThemeModel(title=title)
        async with self.app.database.session.begin() as session:
            session.add(new_theme_model)
        return Theme(id=new_theme_model.id, title=new_theme_model.title)

    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        async with self.app.database.session() as session:
            q = select(ThemeModel).where(ThemeModel.title == title)
            res = (await session.execute(q)).scalars().first()
            if not res:
                return
        return Theme(id=res.id, title=res.title)

    async def get_theme_by_id(self, id_: int) -> Optional[Theme]:
        async with self.app.database.session() as session:
            q = select(ThemeModel).where(ThemeModel.id == id_)
            res = (await session.execute(q)).scalars().first()
            if not res:
                return
        return Theme(id=res.id, title=res.title)

    async def list_themes(self) -> list[Theme]:
        async with self.app.database.session() as session:
            res = (await session.execute(select(ThemeModel))).scalars().all()
        res_list = []
        for row in res:
            res_list.append(Theme(id=row.id, title=row.title))
        return res_list

    async def create_answers(
            self, question_id: int, answers: list[Answer]
    ) -> list[Answer]:
        insert_blk = []
        for i in answers:
            insert_blk.append(AnswerModel(question_id=question_id, title=i.title, is_correct=i.is_correct))
        async with self.app.database.session() as session:
            async with session.begin():
                session.add_all(insert_blk)
        return answers

    async def create_question(
            self, title: str, theme_id: int, answers: list[Answer]
    ) -> Question:
        now_question = QuestionModel(title=title, theme_id=theme_id,
                                     answers=[
                                         AnswerModel(title=ans.title,
                                                     is_correct=ans.is_correct)
                                         for ans in answers
                                     ])
        async with self.app.database.session() as session:
            async with session.begin():
                session.add(now_question)
        question = Question(id=now_question.id, title=title, theme_id=theme_id, answers=answers.copy())
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
            answer_res.append(Answer(title=row.title, is_correct=row.is_correct))
        return Question(id=question.id, title=question.title, theme_id=question.theme_id, answers=answer_res)

    async def list_questions(self, theme_id: Optional[int] = None) -> list[Question]:
        async with self.app.database.session() as session:
            if theme_id:
                q = select(QuestionModel).where(QuestionModel.theme_id == theme_id).options(
                    joinedload(QuestionModel.answers))
            else:
                q = select(QuestionModel).options(joinedload(QuestionModel.answers))
            questions = await session.execute(q)
        res = []
        for question in questions.scalars().unique():
            tmp_anws = []
            for anws in question.answers:
                tmp_anws.append(Answer(title=anws.title, is_correct=anws.is_correct))
            res.append(Question(id=question.id, title=question.title, theme_id=question.theme_id, answers=tmp_anws))
        return res
