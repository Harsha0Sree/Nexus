import uuid
import asyncio
import logging
import traceback
import boto3
from app.config.config import get_settings
from app.infrastructure.postgres import create_pool_connection
from app.infrastructure.repositories import (
    PostgresDocumentRepository,
    PgJobRepository,
    PgAgentRunRepository,
    PgDocumentChunkRepository,
    PgLLMUsageRepository,
    PgPromptRepository
)
from app.infrastructure.storage.s3_storage import S3Storage
from app.infrastructure.llm.openrouter_provider.py import OpenRouterProvider  # wait, correct module is openrouter_provider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider
from app.application.services.agent_orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
)
logger = logging.getLogger("worker")


async def main():
    logger.info('"Starting background worker process"')
    settings = get_settings()
    pool = await create_pool_connection()
    logger.info('"PostgreSQL connection pool established"')

    # Initialize repositories
    doc_repo = PostgresDocumentRepository(pool)
    job_repo = PgJobRepository(pool)
    run_repo = PgAgentRunRepository(pool)
    chunk_repo = PgDocumentChunkRepository(pool)
    usage_repo = PgLLMUsageRepository(pool)
    prompt_repo = PgPromptRepository(pool)

    # Initialize S3 storage
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url
    )
    
    # Auto-create bucket if needed
    try:
        s3_client.create_bucket(Bucket=settings.s3_bucket_name)
        logger.info(f'"Ensured S3 bucket {settings.s3_bucket_name} exists"')
    except Exception as e:
        logger.warning(f'"Failed to create/ensure S3 bucket: {str(e)}"')

    storage = S3Storage(settings.s3_bucket_name, s3_client)

    # Initialize LLM provider
    llm = OpenRouterProvider(settings, usage_repo=usage_repo)

    # Initialize Agent Orchestrator
    orchestrator = AgentOrchestrator(
        doc_repo=doc_repo,
        storage=storage,
        run_repo=run_repo,
        llm=llm,
        chunk_repo=chunk_repo,
        prompt_repo=prompt_repo
    )

    logger.info('"Worker initialization complete. Starting polling loop."')

    try:
        while True:
            try:
                job = await job_repo.claim_next_job()
                if job is None:
                    # No jobs to process, wait 1 second
                    await asyncio.sleep(1.0)
                    continue

                logger.info(f'"Claimed job {str(job.id)} for document {str(job.document_id)}"')

                try:
                    # Run agent orchestrator DAG pipeline
                    await orchestrator.process_document(job.document_id)
                    
                    # Mark job completed
                    await job_repo.mark_completed(job.id)
                    logger.info(f'"Job {str(job.id)} completed successfully"')
                except Exception as e:
                    stack_trace = traceback.format_exc()
                    logger.error(
                        f'"Error processing job {str(job.id)}: {str(e)}"',
                        exc_info=True
                    )
                    
                    # Check attempt counts
                    if job.attempts >= 5:
                        logger.error(f'"Job {str(job.id)} failed after {job.attempts} attempts. Sending to DLQ."')
                        # Exhausted retries -> Send to DLQ
                        try:
                            await job_repo.send_to_dlq(
                                job_id=job.id,
                                document_id=job.document_id,
                                error_message=str(e),
                                stack_trace=stack_trace
                            )
                            await job_repo.mark_failed(job.id, str(e))
                            await doc_repo.update_status(job.document_id, "failed")
                        except Exception as dlq_err:
                            logger.error(f'"Failed to send job {str(job.id)} to DLQ: {str(dlq_err)}"')
                    else:
                        # Reschedule with exponential backoff: 2, 4, 8, 16 seconds
                        backoff_delay = 2 ** job.attempts
                        logger.info(f'"Rescheduling job {str(job.id)} with {backoff_delay} seconds delay"')
                        await job_repo.reschedule_job(job.id, job.attempts, backoff_delay)

            except Exception as loop_err:
                logger.error(f'"Error in worker main loop: {str(loop_err)}"', exc_info=True)
                await asyncio.sleep(2.0)
    finally:
        await llm.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
