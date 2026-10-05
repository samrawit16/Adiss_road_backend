from fastapi import APIRouter, Depends

from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import OAuthCallbackRequest, OAuthUrlResponse, TokenResponse
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


@router.get("/{provider}/url", response_model=OAuthUrlResponse)
def start_oauth(provider: str):
    """Return the provider's consent URL plus a one-time state token."""
    svc = OAuthService(provider)
    url = svc.authorize_url()
    from app.services.oauth_service import _state_store
    state = max(_state_store, key=_state_store.get)
    return OAuthUrlResponse(authorization_url=url, state=state)


@router.post("/{provider}/callback", response_model=TokenResponse)
def oauth_callback(provider: str, body: OAuthCallbackRequest, db=Depends(get_db)):
    """Exchange the provider code for AAGuardian tokens, creating the user
    on first sign-in (email is pre-verified by the provider)."""
    svc = OAuthService(provider)
    claims = svc.exchange_code(body.code, body.state)
    users = UserRepository(db)
    user = users.get_by_email(claims["email"])
    if user is None:
        user = User(
            full_name=claims["name"][:120],
            email=claims["email"],
            phone="",  # providers do not always give a phone
            hashed_password="",  # no password for OAuth-only accounts
            is_verified=True,
            auth_provider=provider,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        from app.core.errors import AuthenticationError
        raise AuthenticationError("Account disabled", "ACCOUNT_DISABLED")
    else:
        user.is_verified = True
        db.commit()
    access, _ = create_access_token(user.id)
    refresh, _ = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)
