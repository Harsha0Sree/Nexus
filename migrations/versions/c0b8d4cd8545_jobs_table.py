"""jobs_table

Revision ID: c0b8d4cd8545
Revises: 803d22ba4727
Create Date: 2026-06-07 21:30:23.171734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0b8d4cd8545'
down_revision: Union[str, Sequence[str], None] = '803d22ba4727'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""CREATE TABLE jobs(
               id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
               document_id UUID NOT NULL REFERENCES users(id),
               status TEXT NOT NULL,
               attempts TEXT,
               started_at TIMESTAMPZ NOT NULL,
               completed_at TIMESTAMPZ NOT NULL,
               created_at TIMESTAMPZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
               error_message TEXT)""")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""DROP TABLE jobs""")
