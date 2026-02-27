from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception.

    Adds a machine-readable ``error_code`` and a ``to_dict()`` helper so the
    global exception handler returns structured API responses:

        {"success": false, "error_code": "NOT_FOUND", "message": "..."}

    Each subclass defines a default ``error_code`` class attribute; callers can
    override it per-raise by passing ``error_code="CUSTOM_CODE"`` to __init__.
    """

    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        error_code: str | None = None,
        headers: dict | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        if error_code is not None:
            self.error_code = error_code

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.detail,
        }


class NotFoundException(AppException):
    error_code = "NOT_FOUND"

    def __init__(
        self,
        detail: str = "Resource not found",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
        )


class UnauthorizedException(AppException):
    error_code = "UNAUTHORIZED"

    def __init__(
        self,
        detail: str = "Invalid credentials",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    error_code = "FORBIDDEN"

    def __init__(
        self,
        detail: str = "Access forbidden",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
        )


class ConflictException(AppException):
    error_code = "CONFLICT"

    def __init__(
        self,
        detail: str = "Resource already exists",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code,
        )


class PaymentRequiredException(AppException):
    error_code = "PAYMENT_REQUIRED"

    def __init__(
        self,
        detail: str = "Premium subscription required",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
            error_code=error_code,
        )


class ValidationException(AppException):
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        detail: str = "Validation error",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code,
        )


class BadGatewayException(AppException):
    error_code = "BAD_GATEWAY"

    def __init__(
        self,
        detail: str = "Upstream service error",
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code=error_code,
        )
