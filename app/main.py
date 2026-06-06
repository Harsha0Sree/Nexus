from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.application.auth_service import AuthService
from app.application.document_service import DocumentService
from app.dependencies.auth import get_auth_service
from app.infrastructure.postgres import create_pool_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool_connection()
    app.state.security = HTTPBearer()
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
async def register_new_user(
    payload: UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    await auth_service.register(payload.email, payload.password)
    return {"message": f"user {payload.email} has been created"}


@app.post("/login")
async def login(
    payload: UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    token = await auth_service.login(payload.email, payload.password)
    if token:
        return token
    return {"message": "invalid credentials"}


@app.get("/documents")
def get_documents(
    document_service: DocumentService,
    credentials=Depends(app.state.security),
):
    document_service=
