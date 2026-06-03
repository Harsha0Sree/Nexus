import datetime
from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str


@dataclass(slots=True)
class Document:
    id: UUID
    user_id: UUID
    file_name: str
    content_hash: str
    created_at: datetime.datetime
    s3_key: str
