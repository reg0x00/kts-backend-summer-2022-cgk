import pytest

from app.bot.models import User, TgUsersModel, TgChatUsersModel, UserChat, SessionModel, BotSession
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
    title = "Which battle ended the French’s attempts to dominate Europe?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            answers=[
                AnswerModel(
                    title="The Battle of Waterloo",
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
    title = "Storming the beaches of Normandy is more commonly known as?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            answers=[
                AnswerModel(
                    title="D-Day",
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


@pytest.fixture
async def question_3(db_session) -> Question:
    title = "How long did the “100 year War” last?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            answers=[
                AnswerModel(
                    title="116 years",
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


@pytest.fixture
async def session_1(db_session) -> BotSession:
    async with db_session.begin() as session:
        user_chat = SessionModel(
            chat_id=120
        )
        session.add(user_chat)

    return BotSession(
        chat_id=user_chat.chat_id
    )


@pytest.fixture
async def user_chat_1(db_session) -> UserChat:
    async with db_session.begin() as session:
        user = TgUsersModel(
            id=100,
            uname="asd"
        )
        user_chat = TgChatUsersModel(
            tg_user=user,
            chat_id=120
        )
        session.add(user_chat)

    return UserChat(
        id=user_chat.id,
        chat_id=user_chat.chat_id,
        uname="asd"
    )


@pytest.fixture
async def user_chat_2(db_session) -> UserChat:
    async with db_session.begin() as session:
        user = TgUsersModel(
            id=200
        )
        user_chat = TgChatUsersModel(
            tg_user=user,
            chat_id=120
        )
        session.add(user_chat)

    return UserChat(
        id=user_chat.id,
        chat_id=user_chat.chat_id
    )


@pytest.fixture
async def user_chat_3(db_session) -> UserChat:
    async with db_session.begin() as session:
        user = TgUsersModel(
            id=300
        )
        user_chat = TgChatUsersModel(
            tg_user=user,
            chat_id=120
        )
        session.add(user_chat)

    return UserChat(
        id=user_chat.id,
        chat_id=user_chat.chat_id
    )
