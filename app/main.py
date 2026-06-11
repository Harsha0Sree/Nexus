import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4
from pydantic import BaseModel
from fastapi import Depends, FastAPI, File, UploadFile, Request, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.application.auth_service import AuthService
from app.application.document_service import DocumentService
from app.dependencies.auth import get_auth_service, get_user
from app.dependencies.document import get_document_service
from app.domain.entities import User
from app.config.config import get_settings
from app.infrastructure.postgres import create_pool_connection
from app.infrastructure.repositories import (
    PgLLMUsageRepository,
    PgDocumentChunkRepository,
    PgPromptRepository
)
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": %(message)s}'
)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool_connection()
    app.state.security = HTTPBearer()
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Log incoming request
    log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown"
    }
    logger.info(json.dumps(log_data))
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Log outgoing response
    response_log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_seconds": round(duration, 4)
    }
    logger.info(json.dumps(response_log_data))
    
    response.headers["X-Request-ID"] = request_id
    return response


class UserCreate(BaseModel):
    email: str
    password: str


class AskRequest(BaseModel):
    question: str


@app.get("/healthz")
def get_healthz():
    return {"status": "ok"}


@app.post("/register")
async def register_new_user(
    payload: UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    await auth_service.register(payload.email, payload.password)
    return {"message": f"user {payload.email} has been created"}


@app.post("/login")
async def login(
    payload: UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    token = await auth_service.login(payload.email, payload.password)
    if token:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid credentials",
    )


@app.post("/documents", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_user),
    document_service: DocumentService = Depends(get_document_service)
):
    content = await file.read()
    doc = await document_service.create_document(
        file_name=file.filename,
        content=content,
        user_id=current_user.id
    )
    return {
        "document_id": str(doc.id),
        "status": "queued"
    }


@app.get("/documents")
async def get_documents(
    current_user: User = Depends(get_user),
    request: Request = None
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM documents WHERE user_id = $1 ORDER BY created_at DESC""",
            current_user.id
        )
        return [
            {
                "id": str(row["id"]),
                "file_name": row["file_name"],
                "status": row.get("status", "pending"),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "classification": row.get("classification"),
                "metadata": json.loads(row["metadata"]) if row.get("metadata") else None,
                "summary": row.get("summary"),
                "risk_analysis": row.get("risk_analysis")
            }
            for row in rows
        ]


@app.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_user),
    request: Request = None
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM documents WHERE id = $1 AND user_id = $2""",
            document_id,
            current_user.id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": str(row["id"]),
            "file_name": row["file_name"],
            "status": row.get("status", "pending"),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "classification": row.get("classification"),
            "metadata": json.loads(row["metadata"]) if row.get("metadata") else None,
            "summary": row.get("summary"),
            "risk_analysis": row.get("risk_analysis")
        }


@app.get("/documents/{document_id}/runs")
async def get_document_runs(
    document_id: UUID,
    current_user: User = Depends(get_user),
    request: Request = None
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        doc_exists = await conn.fetchval(
            "SELECT 1 FROM documents WHERE id = $1 AND user_id = $2",
            document_id,
            current_user.id
        )
        if not doc_exists:
            raise HTTPException(status_code=404, detail="Document not found or unauthorized")

    from app.infrastructure.repositories import PgAgentRunRepository
    run_repo = PgAgentRunRepository(pool)
    runs = await run_repo.get_runs_by_document_id(document_id)
    return [
        {
            "agent_name": run.agent_name,
            "status": run.status.value,
            "retries": run.retries,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
        for run in runs
    ]


@app.post("/documents/{document_id}/ask")
async def ask_question(
    document_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(get_user),
    request: Request = None
):
    settings = get_settings()
    pool = request.app.state.pool

    # Check document ownership
    async with pool.acquire() as conn:
        doc_exists = await conn.fetchval(
            "SELECT 1 FROM documents WHERE id = $1 AND user_id = $2",
            document_id,
            current_user.id
        )
        if not doc_exists:
            raise HTTPException(status_code=404, detail="Document not found or unauthorized")

    usage_repo = PgLLMUsageRepository(pool)
    llm = OpenRouterProvider(settings, usage_repo=usage_repo)
    chunk_repo = PgDocumentChunkRepository(pool)

    try:
        # 1. Embed user question
        question_emb = await llm.embed(payload.question)

        # 2. Vector search similar chunks
        chunks = await chunk_repo.search_similar_chunks(document_id, question_emb, limit=5)
        
        # 3. Compile context
        context = "\n\n".join(c.chunk_text for c in chunks)
        if not context:
            context = "[No relevant context found in document]"

        # 4. Ask Q&A Agent
        system_prompt = (
            "You are a helpful Q&A agent. Answer the user's question using only the provided context. "
            "If the context doesn't contain the answer, explain that context is insufficient but provide a best effort answer."
        )
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question:\n{payload.question}\n\n"
            f"Answer:"
        )
        answer = await llm.generate(prompt, system_prompt=system_prompt)
        return {"answer": answer}
    finally:
        await llm.close()


@app.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics(request: Request):
    pool = request.app.state.pool
    
    async with pool.acquire() as conn:
        # 1. Upload counts
        uploaded = await conn.fetchval("SELECT COUNT(*) FROM documents")
        # 2. Processed counts
        processed = await conn.fetchval("SELECT COUNT(*) FROM documents WHERE status = 'processed'")
        # 3. Agent failures
        failures = await conn.fetchval("SELECT COUNT(*) FROM agent_runs WHERE status = 'failed'")
        # 4. LLM metrics
        usage_row = await conn.fetchrow(
            """SELECT
                 COUNT(*) as requests_total,
                 COALESCE(SUM(cost_usd), 0.0) as cost_total
               FROM llm_usage"""
        )
        # 5. Average job execution time in seconds
        avg_duration = await conn.fetchval(
            """SELECT COALESCE(EXTRACT(EPOCH FROM AVG(completed_at - started_at)), 0.0)
               FROM jobs
               WHERE status = 'completed' AND completed_at IS NOT NULL AND started_at IS NOT NULL"""
        )

    requests_total = usage_row["requests_total"] if usage_row else 0
    cost_total = usage_row["cost_total"] if usage_row else 0.0

    metrics = [
        "# HELP documents_uploaded_total Total documents uploaded to the system.",
        "# TYPE documents_uploaded_total counter",
        f"documents_uploaded_total {uploaded}",
        "",
        "# HELP documents_processed_total Total documents successfully processed.",
        "# TYPE documents_processed_total counter",
        f"documents_processed_total {processed}",
        "",
        "# HELP agent_failures_total Total failed agent runs.",
        "# TYPE agent_failures_total counter",
        f"agent_failures_total {failures}",
        "",
        "# HELP llm_requests_total Total requests sent to LLM providers.",
        "# TYPE llm_requests_total counter",
        f"llm_requests_total {requests_total}",
        "",
        "# HELP llm_cost_usd_total Cumulative cost of LLM tokens in USD.",
        "# TYPE llm_cost_usd_total counter",
        f"llm_cost_usd_total {cost_total:.7f}",
        "",
        "# HELP processing_duration_seconds Average processing duration of document jobs.",
        "# TYPE processing_duration_seconds gauge",
        f"processing_duration_seconds {avg_duration:.3f}"
    ]
    return "\n".join(metrics)
