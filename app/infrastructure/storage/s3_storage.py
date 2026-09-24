import mimetypes
import os

from app.domain.ports import FileStorage
from app.domain.exceptions import UploadSizeExceeded


class S3Storage(FileStorage):
    def __init__(self, bucket_name: str, client, max_size_mb: int = 40):
        self.client = client
        self.bucket = bucket_name
        self.max_file_size = max_size_mb * 1024 * 1024

    async def upload(self, content: bytes, key: str) -> None:
        if len(content) > self.max_file_size:
            raise UploadSizeExceeded(f"File exceeds {self.max_file_size} bytes")

        content_type, _ = mimetypes.guess_type(key)
        if content_type is None:
            content_type = "application/octet-stream"

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return

    async def download(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
        return
