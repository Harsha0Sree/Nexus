import boto3
import pytest
from moto import mock_aws

from app.infrastructure.storage.s3_storage import S3Storage


@pytest.fixture
def setup():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        storage = S3Storage("test_bucket", client)
        client.create_bucket(Bucket="test_bucket")
        yield storage, client


@pytest.mark.asyncio
async def test_s3_storage(setup):
    storage, client = setup
    await storage.upload(content=b"what", file_name="sample.pdf")
    response = client.get_object(
        Bucket="test_bucket",
        Key="sample.pdf",
    )
    assert response["Body"].read() == b"what"
