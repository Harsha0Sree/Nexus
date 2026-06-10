import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.domain.entities import Document
from app.domain.exceptions import CleanUpFailed
from app.domain.ports import (
    DocumentRepository,
    FileStorage,
)


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: FileStorage):
        self.storage = storage
        self.repository = repository

    async def create_document(self, file_name: str, content: bytes, user_id: UUID):
        content_hash = hashlib.sha256(content).hexdigest()
        key = f"documents/{content_hash}{Path(file_name).suffix}"
        uploaded = False
        try:
            await self.storage.upload(content, key)
            uploaded = True
            document = Document(
                id=uuid.uuid4(),
                user_id=user_id,
                file_name=file_name,
                content_hash=content_hash,
                s3_key=key,
                created_at=datetime.now(UTC),
            )
            await self.repository.create(document)
        except Exception:
            if uploaded:
                try:
                    await self.storage.delete(key)
                except Exception:
                    raise CleanUpFailed
        return document
