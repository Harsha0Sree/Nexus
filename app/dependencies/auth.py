from fastapi import Depends, Request, HTTPException, status
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
    
    try:
        user_id = auth_service.verify_access_token(credentials.credentials)
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
