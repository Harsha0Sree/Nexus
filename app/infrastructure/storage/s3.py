import boto3

from app.bizlogic.ports import FileStorage


class S3Storage(FileStorage):
    def __init__(self, bucket_name):
        self.client = boto3.client(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )
        self.bucket = bucket_name
        self.client.create_bucket(Bucket=self.bucket)

    async def upload(self, content, file_name):
        self.client.put_object(Bucket=self.bucket, Key=file_name, Body=content)
        return

    async def download(self, file_name):
        self.client.get_object(Bucket=self.bucket, Key=file_name)
        return
