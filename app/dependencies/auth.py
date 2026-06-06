from fastapi import Request
from fastapi.security import HTTPBearer

from app.application.auth_service import AuthService
from app.infrastructure.repositories import PostgresUserRepository


def get_auth_service(request: Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    return auth_service


async def get_user(request: Request, httpbearer=HTTPBearer()):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    result = auth_service.verify_access_token
    return result
