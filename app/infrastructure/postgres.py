import asyncpg

from app.config.config import get_settings

settings = get_settings()


async def create_pool_connection():
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=10)
    return pool
