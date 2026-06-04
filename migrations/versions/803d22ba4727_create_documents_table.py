"""create documents table

Revision ID: 803d22ba4727
Revises: 669f64c13398
Create Date: 2026-06-01 19:22:20.557512

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "803d22ba4727"
down_revision: Union[str, Sequence[str], None] = "669f64c13398"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""CREATE EXTENSION IF NOT EXISTS pgcrypto;
               CREATE TABLE documents(
               id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
               user_id UUID NOT NULL REFERENCES users(id),
               file_name TEXT NOT NULL ,
               content_hash TEXT NOT NULL,
               s3_key TEXT NOT NULL,
               created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);
               CREATE INDEX idx_documents_user_id
               ON documents(user_id);
               CREATE INDEX idx_document_user_hash
               ON documents(user_id,content_hash)""")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""DROP TABLE documents""")
