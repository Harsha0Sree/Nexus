from fastapi import Request
from app.infrastructure.repositories import PostgresUserRepository
from app.application.auth_service import AuthService


def get_auth_service(request:Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    return auth_service