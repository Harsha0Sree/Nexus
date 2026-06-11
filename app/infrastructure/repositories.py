import uuid
import datetime
from typing import List
from app.domain.entities import (
    Document,
    User,
    Job,
    AgentRun,
    DocumentChunk,
    LLMUsage,
    PromptVersion,
    JobStatus,
    AgentRunStatus
)
from app.domain.ports import (
    UserRepository,
    DocumentRepository,
    JobRepository,
    AgentRunRepository,
    DocumentChunkRepository,
    LLMUsageRepository,
    PromptRepository
)


class PostgresUserRepository(UserRepository):
    def __init__(self, pool):
        self.pool = pool

    async def create(self, user: User) -> User:
        username = user.username or user.email.split("@")[0]
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO users(id, username, email, password_hash)
                   VALUES($1, $2, $3, $4)""",
                user.id,
                username,
                user.email,
                user.password_hash,
            )
            user.username = username
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT * FROM users WHERE email = $1""", email)
            if row:
                return User(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    username=row["username"],
                    created_at=row.get("created_at")
                )
            return None

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT * FROM users WHERE id = $1""", user_id)
            if row:
                return User(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    username=row["username"],
                    created_at=row.get("created_at")
                )
            return None


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, pool):
        self.pool = pool

    async def get_file_by_id(self, document_id: uuid.UUID) -> Document | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM documents WHERE id = $1""", document_id
            )
            if row:
                return Document(
                    id=row["id"],
                    user_id=row["user_id"],
                    file_name=row["file_name"],
                    content_hash=row["content_hash"],
                    s3_key=row["s3_key"],
                    created_at=row["created_at"],
                    status=row.get("status", "pending"),
                    classification=row.get("classification"),
                    metadata=row.get("metadata"),
                    summary=row.get("summary"),
                    risk_analysis=row.get("risk_analysis")
                )
            return None

    async def create(self, document: Document) -> Document | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO documents(id, user_id, file_name, content_hash, s3_key, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (content_hash)
                   DO NOTHING
                   RETURNING *""",
                document.id,
                document.user_id,
                document.file_name,
                document.content_hash,
                document.s3_key,
                document.created_at,
            )
            if row is None:
                return await self.get_file_by_hash(document.content_hash)
            return Document(
                id=row["id"],
                user_id=row["user_id"],
                file_name=row["file_name"],
                content_hash=row["content_hash"],
                s3_key=row["s3_key"],
                created_at=row["created_at"],
                status=row.get("status", "pending"),
                classification=row.get("classification"),
                metadata=row.get("metadata"),
                summary=row.get("summary"),
                risk_analysis=row.get("risk_analysis")
            )

    async def get_file_by_hash(self, content_hash: str) -> Document | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM documents WHERE content_hash = $1""", content_hash
            )
            if row:
                return Document(
                    id=row["id"],
                    user_id=row["user_id"],
                    file_name=row["file_name"],
                    content_hash=row["content_hash"],
                    s3_key=row["s3_key"],
                    created_at=row["created_at"],
                    status=row.get("status", "pending"),
                    classification=row.get("classification"),
                    metadata=row.get("metadata"),
                    summary=row.get("summary"),
                    risk_analysis=row.get("risk_analysis")
                )
            return None

    async def update_status(self, document_id: uuid.UUID, status: str) -> None:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """UPDATE documents SET status = $1 WHERE id = $2""",
                    status,
                    document_id
                )
            except Exception:
                pass

    async def update_document_results(self, document_id: uuid.UUID, classification: str | None = None, metadata: str | None = None, summary: str | None = None, risk_analysis: str | None = None) -> None:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """UPDATE documents
                       SET classification = COALESCE($1, classification),
                           metadata = COALESCE($2::jsonb, metadata),
                           summary = COALESCE($3, summary),
                           risk_analysis = COALESCE($4, risk_analysis)
                       WHERE id = $5""",
                    classification,
                    metadata,
                    summary,
                    risk_analysis,
                    document_id
                )
            except Exception:
                pass


class PgJobRepository(JobRepository):
    def __init__(self, pool):
        self.pool = pool

    async def create_job(self, document_id: uuid.UUID) -> Job:
        job_id = uuid.uuid4()
        status = JobStatus.PENDING.value
        created_at = datetime.datetime.now(datetime.UTC)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO jobs(id, document_id, status, attempts, created_at)
                   VALUES ($1, $2, $3, 0, $4)
                   RETURNING *""",
                job_id,
                document_id,
                status,
                created_at,
            )
            return Job(
                id=row["id"],
                document_id=row["document_id"],
                status=JobStatus(row["status"]),
                attempts=row["attempts"],
                created_at=row["created_at"],
            )

    async def claim_next_job(self) -> Job | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """SELECT * FROM jobs
                       WHERE status = $1 AND created_at <= CURRENT_TIMESTAMP
                       ORDER BY created_at
                       LIMIT 1
                       FOR UPDATE SKIP LOCKED;""",
                    JobStatus.PENDING.value
                )
                if row is None:
                    return None
                
                job_id = row["id"]
                now = datetime.datetime.now(datetime.UTC)
                await conn.execute(
                    """UPDATE jobs
                       SET status = $1, started_at = $2, attempts = attempts + 1
                       WHERE id = $3""",
                    JobStatus.RUNNING.value,
                    now,
                    job_id
                )
                return Job(
                    id=row["id"],
                    document_id=row["document_id"],
                    status=JobStatus.RUNNING,
                    attempts=row["attempts"] + 1,
                    started_at=now,
                    created_at=row["created_at"]
                )

    async def mark_completed(self, job_id: uuid.UUID) -> None:
        now = datetime.datetime.now(datetime.UTC)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE jobs
                   SET status = $1, completed_at = $2
                   WHERE id = $3""",
                JobStatus.COMPLETED.value,
                now,
                job_id
            )

    async def mark_failed(self, job_id: uuid.UUID, error: str) -> None:
        now = datetime.datetime.now(datetime.UTC)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE jobs
                   SET status = $1, completed_at = $2, error_message = $3
                   WHERE id = $4""",
                JobStatus.FAILED.value,
                now,
                error,
                job_id
            )

    async def update_job_status(self, job_id: uuid.UUID, status: JobStatus, attempts: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE jobs
                   SET status = $1, attempts = $2
                   WHERE id = $3""",
                status.value,
                attempts,
                job_id
            )

    async def send_to_dlq(self, job_id: uuid.UUID, document_id: uuid.UUID, error_message: str, stack_trace: str, payload: str | None = None) -> None:
        dlq_id = uuid.uuid4()
        import json
        payload_json = json.dumps({"document_id": str(document_id)}) if payload is None else payload
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO dead_letter_jobs(id, job_id, document_id, error_message, stack_trace, payload)
                   VALUES($1, $2, $3, $4, $5, $6::jsonb)""",
                dlq_id,
                job_id,
                document_id,
                error_message,
                stack_trace,
                payload_json
            )

    async def reschedule_job(self, job_id: uuid.UUID, attempts: int, delay_seconds: int) -> None:
        run_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=delay_seconds)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE jobs
                   SET status = $1, attempts = $2, created_at = $3
                   WHERE id = $4""",
                JobStatus.PENDING.value,
                attempts,
                run_at,
                job_id
            )


class PgAgentRunRepository(AgentRunRepository):
    def __init__(self, pool):
        self.pool = pool

    async def create_run(self, run: AgentRun) -> AgentRun:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO agent_runs(id, document_id, agent_name, status, started_at, retries)
                   VALUES($1, $2, $3, $4, $5, $6)
                   RETURNING *""",
                run.id,
                run.document_id,
                run.agent_name,
                run.status.value,
                run.started_at,
                run.retries
            )
            return AgentRun(
                id=row["id"],
                document_id=row["document_id"],
                agent_name=row["agent_name"],
                status=AgentRunStatus(row["status"]),
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                retries=row["retries"]
            )

    async def update_run_status(self, run_id: uuid.UUID, status: AgentRunStatus, retries: int, error_message: str | None = None) -> None:
        now = datetime.datetime.now(datetime.UTC) if status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED) else None
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE agent_runs
                   SET status = $1, retries = $2, completed_at = $3
                   WHERE id = $4""",
                status.value,
                retries,
                now,
                run_id
            )

    async def get_runs_by_document_id(self, document_id: uuid.UUID) -> List[AgentRun]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM agent_runs WHERE document_id = $1 ORDER BY started_at""",
                document_id
            )
            return [
                AgentRun(
                    id=row["id"],
                    document_id=row["document_id"],
                    agent_name=row["agent_name"],
                    status=AgentRunStatus(row["status"]),
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    retries=row["retries"]
                )
                for row in rows
            ]


class PgDocumentChunkRepository(DocumentChunkRepository):
    def __init__(self, pool):
        self.pool = pool

    async def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for chunk in chunks:
                    # Format float list as string '[0.1, 0.2, ...]' for pgvector
                    vector_str = f"[{','.join(str(x) for x in chunk.embedding)}]" if chunk.embedding else None
                    await conn.execute(
                        """INSERT INTO document_chunks(id, document_id, chunk_text, embedding)
                           VALUES($1, $2, $3, $4::vector)""",
                        chunk.id,
                        chunk.document_id,
                        chunk.chunk_text,
                        vector_str
                    )

    async def search_similar_chunks(self, document_id: uuid.UUID, query_embedding: List[float], limit: int = 5) -> List[DocumentChunk]:
        vector_str = f"[{','.join(str(x) for x in query_embedding)}]"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, document_id, chunk_text, (embedding <=> $1::vector) as distance
                   FROM document_chunks
                   WHERE document_id = $2
                   ORDER BY embedding <=> $1::vector
                   LIMIT $3""",
                vector_str,
                document_id,
                limit
            )
            return [
                DocumentChunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    chunk_text=row["chunk_text"]
                )
                for row in rows
            ]


class PgLLMUsageRepository(LLMUsageRepository):
    def __init__(self, pool):
        self.pool = pool

    async def log_usage(self, usage: LLMUsage) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO llm_usage(id, model, prompt_tokens, completion_tokens, cost_usd)
                   VALUES($1, $2, $3, $4, $5)""",
                usage.id,
                usage.model,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.cost_usd
            )

    async def get_usage_metrics(self) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT
                     COALESCE(SUM(cost_usd), 0.0) as total_cost,
                     COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                     COALESCE(SUM(completion_tokens), 0) as total_completion_tokens
                   FROM llm_usage"""
            )
            return dict(row) if row else {"total_cost": 0.0, "total_prompt_tokens": 0, "total_completion_tokens": 0}


class PgPromptRepository(PromptRepository):
    def __init__(self, pool):
        self.pool = pool

    async def get_prompt_by_name(self, name: str) -> PromptVersion | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM prompt_versions
                   WHERE name = $1
                   ORDER BY version DESC
                   LIMIT 1""",
                name
            )
            if row:
                return PromptVersion(
                    id=row["id"],
                    name=row["name"],
                    version=row["version"],
                    content=row["content"]
                )
            return None

    async def create_prompt_version(self, prompt: PromptVersion) -> PromptVersion:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO prompt_versions(id, name, version, content)
                   VALUES($1, $2, $3, $4)
                   RETURNING *""",
                prompt.id,
                prompt.name,
                prompt.version,
                prompt.content
            )
            return PromptVersion(
                id=row["id"],
                name=row["name"],
                version=row["version"],
                content=row["content"]
            )
