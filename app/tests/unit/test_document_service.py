import uuid

import pytest

from app.application.document_service import DocumentService
from app.bizlogic.entities import Document


class FakeDocumentRepository:
    def __init__(self):
        self.documents = {}

    async def create(self, document: Document):
        self.documents[document.id] = document
        return document

    async def get_file_by_id(self, document_id: uuid.UUID):
        return self.documents.get(document_id)


class FakeStorage:
    def __init__(self):
        self.files = {}

    async def upload(self, content, key):
        self.files[key] = content
        return


@pytest.fixture
def setup_document():
    repo = FakeDocumentRepository()
    storage = FakeStorage()
    service = DocumentService(repository=repo, storage=storage)
    return service, repo, storage


@pytest.mark.asyncio
async def test_create_document(setup_document):
    service, repo, storage = setup_document
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
