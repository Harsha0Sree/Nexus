# Nexus: Multi-Agent Document Processing System

Nexus is a production-grade, asynchronous document processing pipeline built using Python, FastAPI, PostgreSQL (with pgvector), LocalStack (S3), and AI agents orchestrated via a Directed Acyclic Graph (DAG) state machine.

---

## 🏗️ Architecture Overview

The system decouples API request validation from heavy AI computation using a PostgreSQL-backed job queue. This pattern guarantees durability, scalability, and allows the FastAPI gateway to remain highly responsive.

```text
                               +-----------------------------+
                               |        Client (HTTP)        |
                               +--------------+--------------+
                                              |
                                              v
                               +--------------+--------------+
                               |     FastAPI API Gateway     |
                               +-----+--------+--------+-----+
                                     |        |        |
                         1. Store    |        |        | 2. Create
                         File        |        |        |    Background
                                     v        |        v    Job
                               +-----+---+    |    +---+-----+
                               |  AWS S3 |    |    |  Queue  |
                               +---------+    |    +---+-----+
                                              |        |
                                              |        | 3. Claim
                                              |        v
                                              |    +---+-----+
                                              |    |  Worker |
                                              |    +---+-----+
                                              |        |
                                              |        | 4. Run Pipeline
                                              v        v
                               +--------------+--------------+
                               |      Agent Orchestrator     |
                               |  (Coordinator & DAG engine) |
                               +--------------+--------------+
                                              |
      +------------------+--------------------+------------------+------------------+
      | Ingestion        | Classification     | Parallel Meta &  | Embedding        | Risk Analysis
      | Agent            | Agent              | Summarization    | Agent            | Agent (Conditional)
      | (Text & PDF OCR) | (JSON Classifier)  | (async.gather)   | (pgvector index) | (Compliance Review)
      v                  v                    v                  v                  v
+-----+----------+ +-----+----------+  +------+----------+ +-----+----------+ +-----+----------+
|  ExtractedDoc  | |   Doc Type     |  | Meta & Summary  | | Vector Chunks  | | Risk Assessment |
+----------------+ +----------------+  +-----------------+ +----------------+ +-----------------+
```

---

## 🚀 Key Features

* **Decoupled Queue & Worker:** The API handles validation, stores incoming documents in S3, registers background jobs, and responds with `202 Accepted` instantly. Heavy AI orchestrations are claimed and executed asynchronously by workers.
* **Granular Agent DAG Execution:** Decouples agents instead of chaining single-prompt calls.
  1. **Ingestion Agent:** Downloads payloads from S3 and extracts text (utilizing `pypdf` for PDFs, plain text decoding, or dummy fallback).
  2. **Classification Agent:** Infers document types (contract, invoice, resume, research paper, medical report, legal document, or other) using structured JSON output.
  3. **Metadata & Summarization Agents:** Extract key entities, dates, authors, and keywords while concurrently generating executive, detailed, and bullet summaries in parallel (`asyncio.gather`).
  4. **Embedding Agent:** Splits text content into overlapping 500-character chunks, converts them into 1536-dimensional embeddings, and indexes them in PostgreSQL.
  5. **Risk Analysis Agent:** Conditionally executes a legal and compliance risk audit on documents classified as contracts or legal filings.
* **Retrieval-Augmented Generation (RAG):** The `/documents/{id}/ask` endpoint embeds user queries, runs a cosine similarity vector search (`<=>` operator) on indexed document chunks, and prompts the Q&A Agent to provide grounded answers.
* **Reliability Engineering:**
  * **Idempotency:** Re-processing is skipped automatically if a document is already marked as processed.
  * **Exponential Backoff:** Independent agents and worker claims retry up to 5 times on transient errors (with `1s`, `2s`, `4s`, `8s`, `16s` delay backoffs).
  * **Dead Letter Queue (DLQ):** Exhausted jobs are serialized to the `dead_letter_jobs` table along with stack traces and payloads for debugging.
* **Cost & Token Logging:** Token usage and USD costs are logged for every generation and embedding transaction, enabling tracking of costs per user/document/model.
* **Prometheus Metrics:** A `/metrics` endpoint dynamically exports counter metrics on uploads, processing latency, LLM request counts, agent failures, and cumulative token costs.

---

## 📁 Repository Structure

```text
src/ (nexus/)
├── app/
│   ├── domain/                  # Enterprise Domain Layer
│   │   ├── entities.py          # Domain models (User, Document, Job, AgentRun, Chunks, etc.)
│   │   ├── exceptions.py        # Core Domain exception definitions
│   │   └── ports.py             # Repository, Storage, and LLM Protocol contracts
│   │
│   ├── application/             # Business Logic & Orchestration
│   │   ├── auth_service.py      # Registration & JWT Token operations
│   │   ├── document_service.py  # S3 File Storage and job registration coordinator
│   │   └── services/
│   │       └── agent_orchestrator.py # Multi-agent DAG pipeline coordinator
│   │
│   ├── infrastructure/          # Core Infrastructure Adapters
│   │   ├── repositories.py      # PostgreSQL asyncpg repository implementations
│   │   ├── postgres.py          # Pool connection setup & DSN rewrite utilities
│   │   ├── storage/
│   │   │   └── s3_storage.py    # AWS S3 Storage adapter implementation
│   │   └── llm/
│   │       └── openrouter_provider.py # OpenRouter LLM client & Embedding adapter
│   │
│   ├── interface/               # User Interfaces & Entrypoints
│   │   └── api/                 # FastAPI routes (auth, documents, rag, metrics)
│   │
│   ├── dependencies/            # FastAPI Dependency Injection
│   │   ├── auth.py              # JWT authentication dependency resolver
│   │   └── document.py          # Document service dependency resolver
│   │
│   ├── workers/
│   │   └── processor.py         # Long-running background worker loop
│   │
│   ├── tests/                   # Core Test Suite
│   │   └── unit/                # Mock-backed service and orchestrator tests
│   │
│   └── main.py                  # API Application Lifespan & routing entrypoint
│
├── migrations/                  # Alembic DB Migrations directory
│   └── versions/
│       ├── 669f64c13398_create_user_table.py
│       ├── 803d22ba4727_create_documents_table.py
│       ├── c0b8d4cd8545_jobs_table.py
│       └── 46df4a11cbb0_agent_tables.py # Agent runs, vector chunks, LLM usage, DLQ
│
├── compose.yaml                 # Docker Compose development stack configuration
├── pyproject.toml               # Python project configuration and dependency lock
└── uv.lock                      # uv dependency lockfile
```

---

## ⚙️ Environment Configuration

Define your credentials inside a local `.env` file at the project root:

```ini
# Database Connection (Standard PostgreSQL url)
DATABASE_URL=postgres+psycopg://mikey:secret@localhost:5432/nexus
TEST_DATABASE_URL=postgres+psycopg://mikey:secret@localhost:5432/nexus_test

# Authentication Key
JWT_SECRET=yoursecretjwtkeyhere

# LLM Integrations (OpenRouter API)
# Default is gemini-2.5-flash. Change openrouter_api_key to your key.
# If set to 'fake_key', a dummy simulation LLM client runs (perfect for local offline test runs).
OPENROUTER_API_KEY=fake_key
OPENROUTER_MODEL=google/gemini-2.5-flash

# AWS Storage settings (LocalStack / AWS S3)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_ENDPOINT_URL=http://localhost:4566
S3_BUCKET_NAME=nexus-documents
```

---

## 🛠️ Getting Started

### 1. Provision Services
Start the PostgreSQL, Redis, and LocalStack (S3) dependencies using Docker Compose:
```bash
docker compose up -d db redis localstack
```

### 2. Install Dependencies
Nexus uses the fast [uv](https://github.com/astral-sh/uv) package manager:
```bash
# Sync and install virtualenv dependencies
uv sync
```

### 3. Run Database Migrations
Apply Alembic migrations to construct the schemas and register vector support:
```bash
uv run alembic upgrade head
```

### 4. Run the Web Server
Launch the FastAPI API server locally:
```bash
uv run uvicorn app.main:app --reload --port 8000
```
API endpoints are exposed on `http://localhost:8000`. Swagger API documentation is available at `http://localhost:8000/docs`.

### 5. Start the Background Worker
In a separate terminal process, run the queue worker:
```bash
PYTHONPATH=. uv run python app/workers/processor.py
```

---

## 🧪 Running Tests

A mocked testing suite is provided under `app/tests/unit`. It validates password hashing, auth service token mappings, S3 upload checks, and the full multi-agent orchestrator execution flow.

Run tests using `uv`:
```bash
PYTHONPATH=. uv run pytest app/tests/unit/test_hash.py app/tests/unit/test_auth_service.py app/tests/unit/test_document_service.py app/tests/unit/test_s3_storage.py app/tests/unit/test_agent_orchestrator.py
```

---

## 📈 Observability & Monitoring

Nexus logs traces in structured JSON formats containing context variables like `request_id`, `document_id`, `job_id`, and `agent_name`. 

### Prometheus Metrics
Expose active statistics for Prometheus ingestion at `GET /metrics`. Metrics returned include:
* `documents_uploaded_total`: Total files uploaded.
* `documents_processed_total`: Successfully parsed files.
* `agent_failures_total`: Total count of agent execution crashes.
* `llm_requests_total`: Total number of requests dispatched to LLM APIs.
* `llm_cost_usd_total`: Cumulative cost of the processed tokens in USD.
* `processing_duration_seconds`: Live average execution time of successful jobs in seconds.
