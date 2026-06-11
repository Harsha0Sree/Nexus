from app.domain.ports import FileStorage
from app.domain.exceptions import UploadSizeExceeded
max_file_size = 10 * 1024 * 1024


class S3Storage(FileStorage):
    def __init__(self, bucket_name: str, client):
        self.client = client
        self.bucket = bucket_name

    async def upload(self, content, key):
        if len(content)>max_file_size:
            raise UploadSizeExceeded

        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return

    async def download(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)
        return
