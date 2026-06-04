from app.bizlogic.ports import FileStorage


class S3Storage(FileStorage):
    def __init__(self, bucket_name: str, client):
        self.client = client
        self.bucket = bucket_name

    async def upload(self, content, key):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return

    async def download(self, file_name):
        response = self.client.get_object(Bucket=self.bucket, Key=file_name)
        return response
