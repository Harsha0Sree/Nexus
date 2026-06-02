import uuid

import boto3

from app.bizlogic.entities import User
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
                uuid.uuid4(),
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
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

    async def create(self):
        self.client.create_bucket(Bucket="Documents")
        self.client.upload_file("sample.pdf", "Documents")
        self.client.put_object(Bucket="Documents", Key="sample.pdf", Body="")

    async def download(self):
        self.client.get_object(Bucket="Documents", Key="sample.pdf")
