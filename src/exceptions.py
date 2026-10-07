class AppError(Exception):
    def __init__(self, object_name: str | None = None):
        self.object_name = object_name


class UserNotFoundError(AppError): ...


class SessionNotFoundError(AppError): ...
