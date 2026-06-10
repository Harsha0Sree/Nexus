from uuid import UUID

from app.domain.entities import Document, User
from app.domain.ports import DocumentRepository, JobRepository, UserRepository


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
            row = await conn.fetchrow(
                """INSERT INTO documents(id,user_id,file_name,content_hash,s3_key,created_at)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (content_hash)
                DO NOTHING
                RETURNING *""",
                document.id,
                document.user_id,
                document.file_name,
                document.content_hash,
                document.s3_key,
                document.created_at,
            )
            if row is None:
                return None
            return Document(
                file_name=row["file_name"],
                user_id=row["user_id"],
                id=row["id"],
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                s3_key=row["s3_key"],
            )

    async def get_file_by_hash(self, content_hash):
        async with self.pool.acquire as conn:
            row = await conn.fetchrow(
                """SELECT * FROM documents WHERE content_hash = ($1) """, content_hash
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

        return await super().get_file_by_hash(content_hash)


class PgJobRepository(JobRepository):
    async def claim_next_job(self):
        async with self.pool.acquire as conn:
            row = await conn.fetchrow("""BEGIN;
                                      SELECT id FROM jobs
                                      WHERE status ='pending'
                                      ORDER BY created_at
                                      LIMIT 1
                                      FOR UPDATE SKIP LOCKED;""")
            await conn.execute(
                """UPDATE jobs
                SET status = 'running'
                WHERE id = ?;
                COMMIT;""",
                row,
            )
