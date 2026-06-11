import uuid

import pytest

from app.application.document_service import DocumentService
from app.domain.entities import Document


class FakeDocumentRepository:
    def __init__(self):
        self.documents = {}

    async def create(self, document: Document):
        self.documents[document.id] = document
        return document

    async def get_file_by_id(self, document_id: uuid.UUID):
        return self.documents.get(document_id)

    async def get_file_by_hash(self, content_hash: str):
        for doc in self.documents.values():
            if doc.content_hash == content_hash:
                return doc
        return None


class FakeStorage:
    def __init__(self):
        self.files = {}

    async def upload(self, content, key):
        self.files[key] = content
        return

    async def download(self, key):
        return self.files.get(key)

    async def delete(self, key):
        self.files.pop(key, None)
        return


class FakeJobRepository:
    def __init__(self):
        self.jobs = []

    async def create_job(self, document_id: uuid.UUID):
        self.jobs.append(document_id)


@pytest.fixture
def setup_document():
    repo = FakeDocumentRepository()
    storage = FakeStorage()
    job_repo = FakeJobRepository()
    service = DocumentService(repository=repo, storage=storage, job_repo=job_repo)
    return service, repo, storage, job_repo


@pytest.mark.asyncio
async def test_create_document(setup_document):
    service, repo, storage, job_repo = setup_document
    document = await service.create_document(
        user_id=uuid.uuid4(), file_name="sample.pdf", content=b"faoufba"
    )
    assert document.file_name == "sample.pdf"
    assert len(storage.files) == 1
    stored_bytes = next(iter(storage.files.values()))
    assert stored_bytes == b"faoufba"
    assert len(repo.documents) == 1
    stored_doc_metadata = next(iter(repo.documents.values()))
    assert stored_doc_metadata.id == document.id
    assert len(job_repo.jobs) == 1
    assert job_repo.jobs[0] == document.id
