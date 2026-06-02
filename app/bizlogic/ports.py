import uuid
from typing import Protocol

from app.bizlogic.entities import Document, User


class UserRepository(Protocol):
    async def create(self, user: User) -> User: ...

    async def get_user_by_email(self, email: str) -> User | None: ...


class DocumentRepository(Protocol):
    async def create(self, document: Document) -> Document: ...

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None: ...
