import re
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.domain.entities import TokenPair, User
from app.domain.ports import UserRepository
from app.domain.exceptions import UserAlreadyExists, WeakPassword
from app.config.config import get_settings


class AuthService:
    def __init__(self, repository: UserRepository, token_store=None):
        self.repository = repository
        self.token_store = token_store
        self.settings = get_settings()
        self.hasher = PasswordHash.recommended()

    def _validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise WeakPassword("Password must be at least 8 characters long")
        if len(password) > 128:
            raise WeakPassword("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", password):
            raise WeakPassword("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            raise WeakPassword("Password must contain at least one lowercase letter")
        if not re.search(r"\d", password):
            raise WeakPassword("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\[\]]", password):
            raise WeakPassword("Password must contain at least one special character")

    async def register(self, email: str, password: str) -> User:
        self._validate_password(password)
        existing_user = await self.repository.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExists()
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=self.hasher.hash(password),
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
        verify = self.hasher.verify(password, user.password_hash)

        if verify:
            return self._issue_tokens(user.id)
        return None

    def _issue_tokens(self, user_id: UUID) -> TokenPair:
        now = datetime.now(UTC)
        access_payload = {
            "sub": str(user_id),
            "exp": now + timedelta(minutes=self.settings.access_token_ttl_minutes),
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
        refresh_payload = {
            "sub": str(user_id),
            "exp": now + timedelta(days=self.settings.refresh_token_ttl_days),
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        access_token = jwt.encode(
            access_payload, self.settings.jwt_secret, algorithm="HS256"
        )
        refresh_token = jwt.encode(
            refresh_payload,
            self.settings.jwt_secret,
            algorithm="HS256",
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def _decode_token(self, token: str, expected_type: str):
        try:
            payload = jwt.decode(
                token, key=self.settings.jwt_secret, algorithms=["HS256"]
            )
        except ExpiredSignatureError:
            raise ExpiredSignatureError("signature expired")
        except InvalidTokenError:
            raise InvalidTokenError("invalid signature or credentials")
        if payload.get("type") != expected_type:
            raise InvalidTokenError(f"Expected {expected_type} token")
        try:
            user_id = UUID(payload.get("sub"))
        except (ValueError, KeyError):
            raise InvalidTokenError("invalid credentials")
        return payload, user_id

    async def _ensure_not_revoked(self, payload: dict) -> None:
        if not self.token_store:
            return
        token_id = payload.get("jti")
        if token_id and await self.token_store.is_revoked(token_id):
            raise InvalidTokenError("token has been revoked")

    async def verify_access_token(self, access_token: str):
        payload, user_id = self._decode_token(access_token, "access")
        await self._ensure_not_revoked(payload)
        return user_id

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload, user_id = self._decode_token(refresh_token, "refresh")
        await self._ensure_not_revoked(payload)
        await self.revoke_token_payload(payload)
        return self._issue_tokens(user_id)

    async def logout(self, access_token: str | None = None, refresh_token: str | None = None) -> None:
        for token, expected_type in (
            (access_token, "access"),
            (refresh_token, "refresh"),
        ):
            if not token:
                continue
            payload, _ = self._decode_token(token, expected_type)
            await self.revoke_token_payload(payload)

    async def revoke_token_payload(self, payload: dict) -> None:
        if not self.token_store:
            return
        token_id = payload.get("jti")
        expires_at = datetime.fromtimestamp(payload["exp"], UTC)
        if token_id:
            await self.token_store.set_revoked(token_id, expires_at)
