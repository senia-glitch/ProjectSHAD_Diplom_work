from core import CoreError


class UnauthorizedError(CoreError):
    def __init__(self, message: str = "Unauthorized", *, code: int | None = None):
        super().__init__(message, code=code, http_status=401)


class ForbiddenError(CoreError):
    def __init__(self, message: str = "Forbidden", *, code: int | None = None):
        super().__init__(message, code=code, http_status=403)


class TooManyRequestsError(CoreError):
    def __init__(self, message: str = "Too many requests", *, code: int | None = None):
        super().__init__(message, code=code, http_status=429)
