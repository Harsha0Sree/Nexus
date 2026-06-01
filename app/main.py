from fastapi import FastAPI
from pydantic import BaseModel
from app.infrastructure.postgres import create_pool_connection

app = FastAPI()


class UserCreate(BaseModel):
    user_name: str
    email: str
    password: str


@app.get("/healthz")
def get_healthz():
    return {"status": "ok"}


@app.post("/register")
def register_new_user(user: UserCreate):
    auth_service
    
