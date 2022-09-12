import pytest

from app.quiz.models import (
    Answer,
    AnswerModel,
    Question,
    QuestionModel,
)


@pytest.fixture
def answers(store) -> list[Answer]:
    return [
        Answer(title="1"),
        Answer(title="2"),
        Answer(title="3"),
        Answer(title="4"),
    ]


@pytest.fixture
async def question_1(db_session) -> Question:
    title = "how are you?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            answers=[
                AnswerModel(
                    title="well",
                ),
                AnswerModel(
                    title="bad",
                ),
            ],
        )

        session.add(question)

    return Question(
        id=question.id,
        title=title,
        answers=[
            Answer(
                title=a.title,
            )
            for a in question.answers
        ],
    )


@pytest.fixture
async def question_2(db_session) -> Question:
    title = "are you doing fine?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            answers=[
                AnswerModel(
                    title="yep",
                ),
                AnswerModel(
                    title="nop",
                ),
            ],
        )

        session.add(question)

    return Question(
        id=question.id,
        title=question.title,
        answers=[
            Answer(
                title=a.title,
            )
            for a in question.answers
        ],
    )
