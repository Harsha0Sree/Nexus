from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.domain.entities import Document
from app.infrastructure.postgres import create_test_pool_connection
from app.infrastructure.repositories import PostgresDocumentRepository


@pytest.fixture
async def startup():
    pool = await create_test_pool_connection()
    document = Document(
        id=uuid4(),
        user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        file_name="report.pdf",
        content_hash="a1b2c3d4e5f6",
        created_at=datetime.now(),
        s3_key="documents/report.pdf",
    )
    return pool, document


@pytest_asyncio.fixture
async def clean_db(startup):

    pool, _ = startup

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")

    yield

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE documents RESTART IDENTITY CASCADE")


@pytest.mark.asyncio
async def test_create(startup):
    pool, document = startup
    repo = PostgresDocumentRepository(pool)
    row = await repo.create(document)
    assert row is not None
    get_doc = await repo.get_file_by_id(document.id)
    assert get_doc is not None
    assert row.content_hash == get_doc.content_hash
    assert get_doc.id == document.id

    assert get_doc.user_id == document.user_id
    assert get_doc.file_name == document.file_name
    assert get_doc.content_hash == document.content_hash
    assert get_doc.s3_key == document.s3_key
