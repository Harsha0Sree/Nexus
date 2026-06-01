from typing import Protocol

from app.bizlogic.entities import User
from app.infrastructure.postgres import create_pool_connection

pool = create_pool_connection()


class UserRepository(Protocol):
    async def create(self, user: User) -> User: ...

    async def get_user_by_email(self, email: str) -> User | None: ...


class Repository(UserRepository):
    def __init__(self, pool):
        self.pool = pool

    async def create(self):
        with self.pool.acquire() as conn:
            await conn.execute(
                """CREATE TABLE users(
                id INT PRIMARY KEY,
                user_name VARCHAR,
                email VARCHAR,
                password VARCHAR)"""
            )
            conn.commit()
