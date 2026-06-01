from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
