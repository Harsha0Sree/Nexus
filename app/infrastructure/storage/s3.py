from typing import Protocol


class FileStorage(Protocol):
    pass


class S3Storage(FileStorage):
    pass

