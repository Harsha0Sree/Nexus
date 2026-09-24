from __future__ import annotations

from datetime import UTC, datetime


class InMemoryTokenStore:
    def __init__(self):
        self._values: dict[str, datetime] = {}

    async def set_revoked(self, token_id: str, expires_at: datetime) -> None:
        self._values[token_id] = expires_at

    async def is_revoked(self, token_id: str) -> bool:
        expires_at = self._values.get(token_id)
        if not expires_at:
            return False
        if expires_at <= datetime.now(UTC):
            self._values.pop(token_id, None)
            return False
        return True


class RedisTokenStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def set_revoked(self, token_id: str, expires_at: datetime) -> None:
        ttl = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
        await self.redis.set(f"revoked:{token_id}", "1", ex=ttl)

    async def is_revoked(self, token_id: str) -> bool:
        return await self.redis.exists(f"revoked:{token_id}") == 1
