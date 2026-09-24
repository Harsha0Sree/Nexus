from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.application.auth_service import AuthService
from app.infrastructure.repositories import PostgresUserRepository
from app.infrastructure.token_store import InMemoryTokenStore

security = HTTPBearer()


def get_auth_service(request: Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    token_store = getattr(request.app.state, "token_store", InMemoryTokenStore())
    auth_service = AuthService(repository, token_store=token_store)
    return auth_service


async def get_user(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    token_store = getattr(request.app.state, "token_store", InMemoryTokenStore())
    auth_service = AuthService(repository, token_store=token_store)
    
    try:
        user_id = await auth_service.verify_access_token(credentials.credentials)
        if user_id:
            user = await repository.get_user_by_id(user_id)
            if user:
                return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
