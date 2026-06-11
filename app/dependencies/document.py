from fastapi import Request
import boto3
from app.config.config import get_settings
from app.application.document_service import DocumentService
from app.infrastructure.repositories import PostgresDocumentRepository, PgJobRepository
from app.infrastructure.storage.s3_storage import S3Storage


def get_document_service(request: Request) -> DocumentService:
    settings = get_settings()
    pool = request.app.state.pool
    doc_repo = PostgresDocumentRepository(pool)
    job_repo = PgJobRepository(pool)
    
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url
    )
    storage = S3Storage(settings.s3_bucket_name, s3_client)
    
    return DocumentService(repository=doc_repo, storage=storage, job_repo=job_repo)