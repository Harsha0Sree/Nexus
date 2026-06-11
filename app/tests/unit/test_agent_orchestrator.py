import uuid
import pytest
from datetime import datetime, UTC
from app.domain.entities import (
    Document,
    AgentRun,
    DocumentChunk,
    PromptVersion,
    AgentRunStatus
)
from app.application.services.agent_orchestrator import AgentOrchestrator


class MockDocumentRepository:
    def __init__(self):
        self.documents = {}
        self.updates = {}

    async def get_file_by_id(self, document_id: uuid.UUID):
        return self.documents.get(document_id)

    async def update_status(self, document_id: uuid.UUID, status: str):
        if document_id in self.documents:
            self.documents[document_id].status = status

    async def update_document_results(
        self,
        document_id: uuid.UUID,
        classification=None,
        metadata=None,
        summary=None,
        risk_analysis=None
    ):
        if document_id not in self.updates:
            self.updates[document_id] = {}
        if classification:
            self.updates[document_id]["classification"] = classification
            self.documents[document_id].classification = classification
        if metadata:
            self.updates[document_id]["metadata"] = metadata
            self.documents[document_id].metadata = metadata
        if summary:
            self.updates[document_id]["summary"] = summary
            self.documents[document_id].summary = summary
        if risk_analysis:
            self.updates[document_id]["risk_analysis"] = risk_analysis
            self.documents[document_id].risk_analysis = risk_analysis


class MockFileStorage:
    def __init__(self):
        self.files = {}

    async def download(self, key: str):
        return self.files.get(key, b"")


class MockAgentRunRepository:
    def __init__(self):
        self.runs = []

    async def create_run(self, run: AgentRun):
        self.runs.append(run)
        return run

    async def update_run_status(self, run_id: uuid.UUID, status: AgentRunStatus, retries: int, error_message=None):
        for run in self.runs:
            if run.id == run_id:
                run.status = status
                run.retries = retries


class MockLLMProvider:
    def __init__(self):
        self.generate_calls = []
        self.embed_calls = []

    async def generate(self, prompt: str, system_prompt=None):
        self.generate_calls.append((prompt, system_prompt))
        # Return mock JSONs based on the query keyword
        if "classify" in prompt.lower() or (system_prompt and "classify" in system_prompt.lower()):
            return '{"type": "contract", "confidence": 0.95}'
        if "metadata" in prompt.lower() or (system_prompt and "metadata" in system_prompt.lower()):
            return '{"authors": ["Alice"], "companies": ["CorpA"], "dates": ["2026-06-11"], "keywords": ["test"]}'
        if "summar" in prompt.lower() or (system_prompt and "summar" in system_prompt.lower()):
            return "Executive Summary: Success.\nDetailed Summary: High quality.\nBullet Summary: - Done"
        if "risk" in prompt.lower() or (system_prompt and "risk" in system_prompt.lower()):
            return "Risks: None found. Compliance: Standard."
        return "mock text"

    async def embed(self, text: str):
        self.embed_calls.append(text)
        return [0.1] * 1536


class MockDocumentChunkRepository:
    def __init__(self):
        self.chunks = []

    async def save_chunks(self, chunks):
        self.chunks.extend(chunks)


class MockPromptRepository:
    def __init__(self):
        self.prompts = {}

    async def get_prompt_by_name(self, name: str):
        return self.prompts.get(name)

    async def create_prompt_version(self, prompt: PromptVersion):
        self.prompts[prompt.name] = prompt
        return prompt


@pytest.fixture
def setup_orchestrator():
    doc_repo = MockDocumentRepository()
    storage = MockFileStorage()
    run_repo = MockAgentRunRepository()
    llm = MockLLMProvider()
    chunk_repo = MockDocumentChunkRepository()
    prompt_repo = MockPromptRepository()

    orchestrator = AgentOrchestrator(
        doc_repo=doc_repo,
        storage=storage,
        run_repo=run_repo,
        llm=llm,
        chunk_repo=chunk_repo,
        prompt_repo=prompt_repo
    )
    return orchestrator, doc_repo, storage, run_repo, llm, chunk_repo


@pytest.mark.asyncio
async def test_agent_orchestrator_contract_flow(setup_orchestrator):
    orchestrator, doc_repo, storage, run_repo, llm, chunk_repo = setup_orchestrator

    doc_id = uuid.uuid4()
    document = Document(
        id=doc_id,
        user_id=uuid.uuid4(),
        file_name="agreement.pdf",
        content_hash="hash123",
        s3_key="documents/agreement.pdf",
        created_at=datetime.now(UTC),
        status="pending"
    )

    doc_repo.documents[doc_id] = document
    storage.files["documents/agreement.pdf"] = b"This contract represents a mutual agreement between CorpA and Alice."

    # Process document
    await orchestrator.process_document(doc_id)

    # Check status changed
    assert document.status == "processed"

    # Check document results updated
    assert document.classification == "contract"
    assert "Alice" in document.metadata
    assert "Executive Summary" in document.summary
    assert "Risks: None found" in document.risk_analysis

    # Check agent runs created and completed
    # Should have runs for Ingestion, Classification, Metadata, Summarization, Embedding, Risk Analysis
    agent_names = [r.agent_name for r in run_repo.runs]
    assert "ingestion" in agent_names
    assert "classification" in agent_names
    assert "metadata" in agent_names
    assert "summarization" in agent_names
    assert "embedding" in agent_names
    assert "risk_analysis" in agent_names
    for run in run_repo.runs:
        assert run.status == AgentRunStatus.COMPLETED

    # Check chunks saved
    assert len(chunk_repo.chunks) > 0
    assert chunk_repo.chunks[0].document_id == doc_id
