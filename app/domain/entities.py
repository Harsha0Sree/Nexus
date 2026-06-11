import datetime
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    username: str = ""
    created_at: datetime.datetime | None = None


@dataclass(slots=True)
class Document:
    id: UUID
    user_id: UUID
    file_name: str
    content_hash: str
    created_at: datetime.datetime
    s3_key: str
    status: str = "pending"
    classification: str | None = None
    metadata: str | None = None
    summary: str | None = None
    risk_analysis: str | None = None


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(slots=True)
class Job:
    id: UUID
    document_id: UUID
    status: JobStatus
    attempts: int
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None
    error_message: str | None = None


@dataclass(slots=True)
class ExtractedDocument:
    title: str
    content: str
    pages: int


@dataclass(slots=True)
class AgentRun:
    id: UUID
    document_id: UUID
    agent_name: str
    status: AgentRunStatus
    started_at: datetime.datetime
    completed_at: datetime.datetime | None = None
    retries: int = 0


@dataclass(slots=True)
class DocumentChunk:
    id: UUID
    document_id: UUID
    chunk_text: str
    embedding: list[float] | None = None


@dataclass(slots=True)
class LLMUsage:
    id: UUID
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass(slots=True)
class PromptVersion:
    id: UUID
    name: str
    version: int
    content: str
