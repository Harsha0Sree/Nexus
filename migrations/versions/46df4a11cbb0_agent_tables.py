"""agent_tables

Revision ID: 46df4a11cbb0
Revises: c0b8d4cd8545
Create Date: 2026-06-11 11:15:00.000000

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46df4a11cbb0"
down_revision: Union[str, Sequence[str], None] = "c0b8d4cd8545"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable vector extension for pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Add status and results columns to documents
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification TEXT;")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata JSONB;")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_analysis TEXT;")

    # Create agent_runs table
    op.execute("""
        CREATE TABLE agent_runs (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMPTZ,
            retries INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX idx_agent_runs_document_id ON agent_runs(document_id);
    """)

    # Create document_chunks table
    op.execute("""
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            embedding VECTOR(1536)
        );
        CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
    """)

    # Create llm_usage table
    op.execute("""
        CREATE TABLE llm_usage (
            id UUID PRIMARY KEY,
            model TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            cost_usd NUMERIC(10, 7) NOT NULL
        );
    """)

    # Create prompt_versions table
    op.execute("""
        CREATE TABLE prompt_versions (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            version INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, version)
        );
    """)

    # Create dead_letter_jobs table
    op.execute("""
        CREATE TABLE dead_letter_jobs (
            id UUID PRIMARY KEY,
            job_id UUID NOT NULL,
            document_id UUID NOT NULL,
            error_message TEXT,
            stack_trace TEXT,
            failed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            payload JSONB
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS dead_letter_jobs;")
    op.execute("DROP TABLE IF EXISTS prompt_versions;")
    op.execute("DROP TABLE IF EXISTS llm_usage;")
    op.execute("DROP TABLE IF EXISTS document_chunks;")
    op.execute("DROP TABLE IF EXISTS agent_runs;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS risk_analysis;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS summary;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS metadata;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS classification;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS status;")
