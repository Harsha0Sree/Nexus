from fastapi import Request

from app.infrastructure.repositories import PostgresDocumentRepository


def get_database_service(request: Request):
    pool = request.app.state.pool
    repo = PostgresDocumentRepository(pool)
    return repo
