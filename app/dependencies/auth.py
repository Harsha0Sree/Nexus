import uuid
from fastapi import Request
from app.domain.entities import User
from app.application.auth_service import AuthService
from app.infrastructure.repositories import PostgresUserRepository


def get_auth_service(request: Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    return auth_service


async def get_user(request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Resolve or auto-create a default system user to bypass auth
        row = await conn.fetchrow("SELECT * FROM users LIMIT 1")
        if row:
            return User(
                id=row["id"],
                email=row["email"],
                password_hash=row["password_hash"],
                username=row["username"]
            )
        
        default_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        await conn.execute(
            """INSERT INTO users (id, username, email, password_hash)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT DO NOTHING""",
            default_id,
            "system_user",
            "system@nexus.ai",
            "nopassword"
        )
        return User(
            id=default_id,
            email="system@nexus.ai",
            password_hash="nopassword",
            username="system_user"
        )
