from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth_service import AuthService
from app.infrastructure.repositories import PostgresUserRepository

security = HTTPBearer()


def get_auth_service(request: Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    return auth_service


async def get_user(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    user_id = auth_service.verify_access_token(credentials.credentials)
    if user_id:
        user = 
    return 

