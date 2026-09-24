class DomainError(Exception):
    pass


class UserAlreadyExists(DomainError):
    pass


class CleanUpFailed(DomainError):
    pass


class UploadSizeExceeded(DomainError):
    pass


class WeakPassword(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class InvalidFileType(DomainError):
    pass


class FileTooLarge(DomainError):
    pass
