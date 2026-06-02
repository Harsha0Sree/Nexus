from fastapi import FastAPI
from pydantic import BaseModel

from app.application.auth_service import AuthService
from app.infrastructure.postgres import create_pool_connection
from app.infrastructure.repositries import PostgresUserRepository

app = FastAPI()
pool = create_pool_connection()


class UserCreate(BaseModel):
    email: str
    password: str


@app.get("/healthz")
def get_healthz():
    return {"status": "ok"}


@app.post("/register")
async def register_new_user(payload: UserCreate):
    repository = PostgresUserRepository(pool)
    auth_service = AuthService(repository)
    await auth_service.register(payload.email, payload.password)
