from dataclasses import dataclass

from app.quiz.models import Question


@dataclass
class User:
    id: int
    uname: str
    chat_id: list[int]


@dataclass
class LastSession:
    chat_id: int
    lead: User
    completed_questions: int
    correct_questions: int


@dataclass
class SessionQuestion:
    question: Question
    started_date: int
    completed_questions: int
    correct_questions: int
    lead: User
    respondent: User | None = None


@dataclass
class BotSession:
    chat_id: int
    session_question: SessionQuestion | None = None
    last_session: LastSession | None = None

    def check_answer(self, ans: str):
        return self.session_question and ans in [a.title for a in self.session_question.question.answers]
