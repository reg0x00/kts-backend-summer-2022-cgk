from dataclasses import dataclass


@dataclass
class UpdateMessage:
    date: int
    from_id: int
    chat_id: int
    text: str
    from_username: str
    is_command: bool = False
    is_mention: bool = False


@dataclass
class Update:
    update_id: int
    object: UpdateMessage


@dataclass
class Message:
    user_id: int
    text: str
