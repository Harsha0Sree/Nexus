import uuid

import pytest

from app.application.auth_service import AuthService, UserAlreadyExists
from app.bizlogic.entities import User


class FakeUserRepository:
    def __init__(self):
        self.users = {}

    async def create(self, user: User):
        self.users[user.email] = user
        return user

    async def get_user_by_email(self, email: str):
        return self.users.get(email)


@pytest.fixture
def setup():
    repo = FakeUserRepository()
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
    )
    service = AuthService(repo)
    return service, user


@pytest.mark.asyncio
async def test_register_creates_user(setup):
    service, user = setup
    created_user = await service.register(user)
    assert created_user.email == user.email


@pytest.mark.asyncio
async def test_check_existing_user(setup):
    service, user = setup
    await service.register(user)
    with pytest.raises(UserAlreadyExists):
        await service.register(user)
    assert await service.get_user_by_email(user.email) is not None
    
