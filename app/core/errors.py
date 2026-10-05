from fastapi import HTTPException, status

class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ValidationError(AppError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code, status.HTTP_422_UNPROCESSABLE_ENTITY)

class EmailDeliveryFailed(AppError):
    """The email provider refused or could not be reached (HTTP 503)."""
    def __init__(self, message: str = "We could not send the email right now. Please try again in a few minutes.",
                 code: str = "EMAIL_SEND_FAILED"):
        super().__init__(message, code, status.HTTP_503_SERVICE_UNAVAILABLE)

class AuthenticationError(AppError):
    def __init__(self, message: str = "Invalid email or password", code: str = "AUTH_ERROR"):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED)

class AuthorizationError(AppError):
    """Authenticated, but not allowed (HTTP 403). Distinct from a bad/expired token (401)."""
    def __init__(self, message: str = "Not allowed", code: str = "FORBIDDEN"):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN)

class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(message, code, status.HTTP_409_CONFLICT)

class NotFoundError(AppError):
    def __init__(self, message: str, code: str = "NOT_FOUND"):
        super().__init__(message, code, status.HTTP_404_NOT_FOUND)
