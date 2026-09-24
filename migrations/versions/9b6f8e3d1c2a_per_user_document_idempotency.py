"""per_user_document_idempotency

Revision ID: 9b6f8e3d1c2a
Revises: 46df4a11cbb0
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "9b6f8e3d1c2a"
down_revision: Union[str, Sequence[str], None] = "46df4a11cbb0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_content_hash_key;")
    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_user_content_hash
           ON documents(user_id, content_hash);"""
    )
    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_active_document
           ON jobs(document_id)
           WHERE status IN ('pending', 'running');"""
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_jobs_active_document;")
    op.execute("DROP INDEX IF EXISTS uq_documents_user_content_hash;")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_content_hash_key UNIQUE(content_hash);")
