import uuid
from typing import Protocol

from app.bizlogic.entities import Document, User


class UserRepository(Protocol):
    async def create(self, user: User) -> User: ...

    async def get_user_by_email(self, email: str) -> User | None: ...


class DocumentRepository(Protocol):
    async def create(self, document: Document) -> Document: ...

    async def get_file_by_id(self, document_id: uuid.UUID) -> Document | None: ...


class FileStorage(Protocol):
    async def upload(self, content: bytes, key: str) -> None: ...

    async def download(self, key: str) -> bytes: ...
