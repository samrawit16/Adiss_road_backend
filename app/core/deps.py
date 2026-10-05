from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
                     db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise AuthenticationError("Not authenticated")
    payload = decode_token(creds.credentials)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthenticationError("User not found")
    return user
