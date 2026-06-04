from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.application.auth_service import AuthService
from app.infrastructure.postgres import create_pool_connection
from app.infrastructure.repositories import PostgresUserRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool_connection()
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)


class UserCreate(BaseModel):
    email: str
    password: str


@app.get("/healthz")
def get_healthz():
    return {"status": "ok"}


@app.post("/register")
async def register_new_user(payload: UserCreate, request: Request):
    pool = request.app.state.pool
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    await auth_service.register(payload.email, payload.password)
