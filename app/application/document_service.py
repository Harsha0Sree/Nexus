import uuid

from pwdlib import PasswordHash

from app.bizlogic.entities import User
from app.infrastructure.repositories import DocumentRepository


class DocumentService:
    def __init__(self, repository: DocumentRepository):
        self.repository = repository
