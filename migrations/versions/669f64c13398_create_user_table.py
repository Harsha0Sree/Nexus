"""create user table

Revision ID: 669f64c13398
Revises:
Create Date: 2026-05-29 19:25:33.038094

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "669f64c13398"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""CREATE TABLE users(
               id UUID PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
               email TEXT NOT NULL UNIQUE,
               password_hash TEXT NOT NULL,
               created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""DROP TABLE users""")
