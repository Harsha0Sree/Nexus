import datetime
import hashlib
import uuid
from pathlib import Path
from uuid import UUID

from app.bizlogic.entities import Document
from app.bizlogic.ports import (
    DocumentRepository,
    FileStorage,
)


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: FileStorage):
        self.storage = storage
        self.repository = repository

    async def create_document(self, user_id: UUID, file_name: str, content: bytes):
        content_hash = hashlib.sha512(content).hexdigest()
        key = f"users/{uuid.uuid4()}{Path(file_name).suffix}"
        await self.storage.upload(content, file_name, user_id)
        document = Document(
            id=uuid.uuid4(),
            user_id=user_id,
            file_name=file_name,
            content_hash=content_hash,
            s3_key=key,
            created_at=datetime.utcnow(),
        )
        self.repository.create(document)
