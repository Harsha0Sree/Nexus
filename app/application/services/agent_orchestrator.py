import io
import json
import uuid
import asyncio
import traceback
from datetime import datetime, UTC
from pypdf import PdfReader
from app.domain.entities import (
    Document,
    ExtractedDocument,
    AgentRun,
    AgentRunStatus,
    DocumentChunk,
    PromptVersion
)
from app.domain.ports import (
    DocumentRepository,
    FileStorage,
    AgentRunRepository,
    LLMProvider,
    DocumentChunkRepository,
    PromptRepository
)

class AgentOrchestrator:
    def __init__(
        self,
        doc_repo: DocumentRepository,
        storage: FileStorage,
        run_repo: AgentRunRepository,
        llm: LLMProvider,
        chunk_repo: DocumentChunkRepository,
        prompt_repo: PromptRepository
    ):
        self.doc_repo = doc_repo
        self.storage = storage
        self.run_repo = run_repo
        self.llm = llm
        self.chunk_repo = chunk_repo
        self.prompt_repo = prompt_repo

    async def get_prompt(self, name: str, default_content: str) -> str:
        try:
            prompt_version = await self.prompt_repo.get_prompt_by_name(name)
            if prompt_version:
                return prompt_version.content
            # Save default prompt if not exists
            new_prompt = PromptVersion(
                id=uuid.uuid4(),
                name=name,
                version=1,
                content=default_content
            )
            await self.prompt_repo.create_prompt_version(new_prompt)
            return default_content
        except Exception:
            return default_content

    async def execute_with_retry(self, agent_name: str, doc_id: uuid.UUID, func, *args, **kwargs):
        # Create agent run entry
        run = AgentRun(
            id=uuid.uuid4(),
            document_id=doc_id,
            agent_name=agent_name,
            status=AgentRunStatus.RUNNING,
            started_at=datetime.now(UTC),
            retries=0
        )
        await self.run_repo.create_run(run)

        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                await self.run_repo.update_run_status(run.id, AgentRunStatus.COMPLETED, attempt)
                return result
            except Exception as e:
                last_error = e
                # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                delay = 2 ** attempt
                await asyncio.sleep(delay)
        
        # Exhausted retries
        error_msg = f"{type(last_error).__name__}: {str(last_error)}"
        await self.run_repo.update_run_status(run.id, AgentRunStatus.FAILED, max_retries, error_message=error_msg)
        raise last_error

    async def process_document(self, document_id: uuid.UUID):
        document = await self.doc_repo.get_file_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Idempotency
        if document.status == "processed":
            return

        await self.doc_repo.update_status(document_id, "processing")

        try:
            # 1. Ingestion Agent
            extracted_doc = await self.execute_with_retry(
                "ingestion", document_id, self._run_ingestion_agent, document
            )

            # 2. Classification Agent
            classification = await self.execute_with_retry(
                "classification", document_id, self._run_classification_agent, extracted_doc
            )
            await self.doc_repo.update_document_results(document_id, classification=classification)

            # 3. Parallel Agents: Metadata & Summarization
            async def run_meta():
                meta = await self.execute_with_retry(
                    "metadata", document_id, self._run_metadata_agent, extracted_doc, classification
                )
                await self.doc_repo.update_document_results(document_id, metadata=json.dumps(meta))

            async def run_sum():
                summary = await self.execute_with_retry(
                    "summarization", document_id, self._run_summarization_agent, extracted_doc
                )
                await self.doc_repo.update_document_results(document_id, summary=summary)

            await asyncio.gather(run_meta(), run_sum())

            # 4. Embedding Agent
            await self.execute_with_retry(
                "embedding", document_id, self._run_embedding_agent, document_id, extracted_doc
            )

            # 5. Risk Analysis Agent (Conditional execution)
            if classification in ("contract", "medical report", "legal document"):
                risk_analysis = await self.execute_with_retry(
                    "risk_analysis", document_id, self._run_risk_analysis_agent, extracted_doc
                )
                await self.doc_repo.update_document_results(document_id, risk_analysis=risk_analysis)

            await self.doc_repo.update_status(document_id, "processed")

        except Exception as e:
            await self.doc_repo.update_status(document_id, "failed")
            raise e

    # --- Agent Implementations ---

    async def _run_ingestion_agent(self, document: Document) -> ExtractedDocument:
        content_bytes = await self.storage.download(document.s3_key)
        
        # Determine file type
        suffix = document.file_name.split(".")[-1].lower() if "." in document.file_name else ""
        
        title = document.file_name
        content_text = ""
        pages = 1

        if suffix == "pdf":
            try:
                pdf_file = io.BytesIO(content_bytes)
                reader = PdfReader(pdf_file)
                pages = len(reader.pages)
                extracted_pages = []
                for p in reader.pages:
                    text = p.extract_text()
                    if text:
                        extracted_pages.append(text)
                content_text = "\n".join(extracted_pages)
            except Exception as e:
                # If PDF reading fails, fallback to converting bytes to text
                content_text = content_bytes.decode("utf-8", errors="ignore")
        elif suffix in ("txt", "json", "xml", "csv"):
            content_text = content_bytes.decode("utf-8", errors="ignore")
        else:
            # Fallback for docx or image, decoded as string or mock OCR text
            content_text = content_bytes.decode("utf-8", errors="ignore")
            if not content_text.strip():
                content_text = f"[Binary Document: {document.file_name} of size {len(content_bytes)} bytes]"

        return ExtractedDocument(
            title=title,
            content=content_text,
            pages=pages
        )

    async def _run_classification_agent(self, doc: ExtractedDocument) -> str:
        default_prompt = (
            "Classify the following document content into exactly one of these types: "
            "contract, invoice, research paper, resume, medical report, legal document, or other.\n"
            "Return ONLY a JSON object like: {\"type\": \"contract\", \"confidence\": 0.95}\n\n"
            "Document content:\n{content}"
        )
        system_prompt = "You are an expert document classification agent. Output strict JSON."
        
        template = await self.get_prompt("classification_agent", default_prompt)
        prompt = template.replace("{content}", doc.content[:4000])

        response = await self.llm.generate(prompt, system_prompt=system_prompt)
        
        # Clean response and parse JSON
        cleaned = self._clean_json_response(response)
        try:
            data = json.loads(cleaned)
            return data.get("type", "other").lower()
        except Exception:
            return "other"

    async def _run_metadata_agent(self, doc: ExtractedDocument, classification: str) -> dict:
        default_prompt = (
            "Extract entities from the document content. The document type is: {type}.\n"
            "Return a JSON object with strictly these keys: authors (list of strings), "
            "companies (list of strings), dates (list of strings in format YYYY-MM-DD), and keywords (list of strings).\n\n"
            "Content:\n{content}"
        )
        system_prompt = "You are a metadata extraction agent. Output strict JSON."
        
        template = await self.get_prompt("metadata_agent", default_prompt)
        prompt = template.replace("{type}", classification).replace("{content}", doc.content[:4000])

        response = await self.llm.generate(prompt, system_prompt=system_prompt)
        
        cleaned = self._clean_json_response(response)
        try:
            return json.loads(cleaned)
        except Exception:
            return {"authors": [], "companies": [], "dates": [], "keywords": []}

    async def _run_summarization_agent(self, doc: ExtractedDocument) -> str:
        default_prompt = (
            "Provide three summaries of the following document content:\n"
            "1. EXECUTIVE SUMMARY: A high-level overview.\n"
            "2. DETAILED SUMMARY: A comprehensive explanation.\n"
            "3. BULLET SUMMARY: Key bullet points.\n\n"
            "Content:\n{content}"
        )
        system_prompt = "You are a summarization agent. Use clean markdown formatting."
        
        template = await self.get_prompt("summarization_agent", default_prompt)
        prompt = template.replace("{content}", doc.content[:6000])

        response = await self.llm.generate(prompt, system_prompt=system_prompt)
        return response

    async def _run_embedding_agent(self, doc_id: uuid.UUID, doc: ExtractedDocument) -> None:
        # 1. Chunking text: 500 characters, 100 character overlap
        text = doc.content
        chunk_size = 500
        overlap = 100
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append(chunk_text)
            start += chunk_size - overlap
            # Break if we are at the end
            if end >= len(text):
                break

        if not chunks:
            chunks.append("[Empty Document]")

        # 2. Embed each chunk and prepare objects
        chunk_entities = []
        for c_text in chunks:
            embedding = await self.llm.embed(c_text)
            chunk_entities.append(DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                chunk_text=c_text,
                embedding=embedding
            ))

        # 3. Batch save chunks
        await self.chunk_repo.save_chunks(chunk_entities)

    async def _run_risk_analysis_agent(self, doc: ExtractedDocument) -> str:
        default_prompt = (
            "Analyze the document content for risks, missing clauses, or compliance issues.\n"
            "Document content:\n{content}"
        )
        system_prompt = "You are a legal and compliance risk analysis agent. Highlight risks and missing clauses clearly."
        
        template = await self.get_prompt("risk_analysis_agent", default_prompt)
        prompt = template.replace("{content}", doc.content[:5000])

        response = await self.llm.generate(prompt, system_prompt=system_prompt)
        return response

    def _clean_json_response(self, text: str) -> str:
        # Strip markdown block code if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
