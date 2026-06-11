import asyncpg

from app.config.config import get_settings

settings = get_settings()


def get_asyncpg_dsn(dsn: str) -> str:
    if dsn.startswith("postgres+psycopg://"):
        return dsn.replace("postgres+psycopg://", "postgresql://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql://", 1)
    return dsn


async def create_pool_connection():
    dsn = get_asyncpg_dsn(settings.database_url)
    pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    return pool

async def create_test_pool_connection():
    dsn = get_asyncpg_dsn(settings.test_database_url)
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=3)
    return pool
