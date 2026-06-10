class DomainError(Exception):
    pass


class UserAlreadyExists(DomainError):
    pass


class CleanUpFailed(DomainError):
    pass

class UploadSizeExceeded(DomainError):
    pass