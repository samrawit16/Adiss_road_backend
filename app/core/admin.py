from fastapi import Depends

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import AuthorizationError
from app.models.user import User


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only active accounts whose email is in ADMIN_EMAILS (or is the default admin).

    A missing/expired token is a 401 (raised by get_current_user). A valid token that
    belongs to a non-admin is a 403 - the dashboard must not treat that as "session
    expired", otherwise it loops back to the login page forever.
    """
    if not current_user.is_active:
        raise AuthorizationError("Account disabled", "ACCOUNT_DISABLED")
    if current_user.email.strip().lower() not in settings.admin_email_set:
        raise AuthorizationError("Admin access required", "ADMIN_REQUIRED")
    return current_user
