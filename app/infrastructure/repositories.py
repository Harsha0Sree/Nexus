from uuid import UUID

from app.bizlogic.entities import Document, User
from app.bizlogic.ports import DocumentRepository, UserRepository


class PostgresUserRepository(UserRepository):
    def __init__(self, pool):
        self.pool = pool

    async def create(self, user: User):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO users(email,password_hash,id) VALUES($1,$2,$3)""",
                user.email,
                user.password_hash,
                user.id,
            )

            return user

    async def get_user_by_email(self, email):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT * FROM users WHERE email = $1""", email)
            if row:
                return User(
                    id=row["id"], email=row["email"], password_hash=row["password_hash"]
                )
            return None


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, pool):
        self.pool = pool

    async def get_file_by_id(self, document_id: UUID):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM documents WHERE id = ($1)""", document_id
            )
            if row:
                return Document(
                    file_name=row["filename"],
                    user_id=row["user_id"],
                    id=row["id"],
                    content_hash=row["content_hash"],
                    created_at=row["created_at"],
                    s3_key=row["s3_key"],
                )
            return None

    async def create(self, document: Document):
        async with self.pool.acquire() as conn:
            row = await conn.execute(
                """INSERT INTO documents(id,user_id,file_name,content_hash,s3_key,created_at) VALUES ($1,$2,$3,$4,$5,$6)""",
                document.id,
                document.user_id,
                document.file_name,
                document.content_hash,
                document.s3_key,
                document.created_at,
            )
            return row
