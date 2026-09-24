import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.domain.entities import Document
from app.domain.exceptions import CleanUpFailed, FileTooLarge, InvalidFileType
from app.domain.ports import DocumentRepository, FileStorage, JobRepository
from app.config.config import get_settings


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_MAX_FILE_SIZE_MB = None  # lazy-loaded from settings


def _get_max_file_size() -> int:
    global _MAX_FILE_SIZE_MB
    if _MAX_FILE_SIZE_MB is None:
        _MAX_FILE_SIZE_MB = get_settings().max_file_size_mb
    return _MAX_FILE_SIZE_MB


def _secure_filename(filename: str) -> str:
    filename = filename.strip().replace(" ",的", "_")
    filename = re.sub(r"[^\w\-_\.]", "_", filename)
    if not filename or filename == "." or filename == "..":
        return "unnamed"
    return filename


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: FileStorage,
        job_repo: JobRepository,
    ):
        self.storage = storage
        self.repository = repository
        self.job_repo = job_repo
        self._max_size_mb = _get_max_file_size()

    async def create_document(self, file_name: str, content: bytes, user_id: UUID):
        max_size = self._max_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise FileTooLarge(f"File exceeds {self._max_size_mb}MB limit")

        secure_name = _secure_filename(file_name)
        ext = Path(secure_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileType(f"Unsupported file type: {ext}")

        content_hash = hashlib.sha256(content).hexdigest()
        key = f"documents/{content_hash}{ext}"
        uploaded = False
        try:
            await self.storage.upload(content, key)
            uploaded = True
            document = Document(
                id=uuid.uuid4(),
                user_id=user_id,
                file_name=secure_name,
                content_hash=content_hash,
                s3_key=key,
                created_at=datetime.now(UTC),
            )
            document = await self.repository.create(document)
            if document and document.status in {"pending", "failed"}:
                await self.job_repo.create_job(document.id)
        except Exception:
            if uploaded:
                try:
                    await self.storage.delete(key)
                except Exception:
                    raise CleanUpFailed()
            raise
        return document
