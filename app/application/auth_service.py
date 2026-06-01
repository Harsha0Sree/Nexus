from app.bizlogic.entities import User


class UserAlreadyExists(Exception):
    pass


class AuthService:
    def register(self, email: str) -> User:
        existing_user = repository.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExists()
        new_user = repository.create(User())
