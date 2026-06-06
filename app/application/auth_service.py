import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.bizlogic.entities import TokenPair, User, UserRepository
from app.config.config import get_settings


class UserAlreadyExists(Exception):
    pass


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
        self.settings = get_settings()

    async def register(self, email: str, password: str) -> User:
        existing_user = await self.repository.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExists()
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=PasswordHash().recommended().hash(password),
        )
        return await self.repository.create(user)

    async def get_user_by_email(self, email: str) -> User | None:
        user = await self.repository.get_user_by_email(email)
        if user:
            return user
        return None

    async def login(self, email: str, password: str):
        user = await self.repository.get_user_by_email(email)
        if not user:
            return None
        verify = PasswordHash().verify(user.password_hash, password)
        access_payload = {
            "user": str(user.id),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "type": "access",
        }
        refresh_payload = {
            "user": str(user.id),
            "exp": datetime.now(UTC) + timedelta(days=30),
            "type": "refresh",
        }
        if verify:
            access_token = jwt.encode(
                access_payload, secrets.token_hex(32), algorithm="HS256"
            )
            refresh_token = jwt.encode(
                refresh_payload,
                self.settings.jwt_secret,
                algorithm="HS256",
            )
            return TokenPair(access_token=access_token, refresh_token=refresh_token)
        return verify
