import uuid

from pwdlib import PasswordHash

from app.bizlogic.entities import User
from app.bizlogic.entities import UserRepository


class UserAlreadyExists(Exception):
    pass


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def register(self, email: str, password: str) -> User:
        existing_user = await self.repository.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExists()
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=PasswordHash.recommended().hash(password),
        )
        return self.repository.create(user)

    async def get_user_by_email(self, email: str) -> User | None:
        user = await self.repository.get_user_by_email(email)
        if user:
            return user
        return None
