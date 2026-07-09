"""Authentication endpoints: register, login, Google sign-in, current user."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import GoogleAuthError, InvalidCredentialsError, UserAlreadyExistsError
from app.models.user import User
from app.schemas.auth import AuthConfig, GoogleAuthRequest, Token, UserCreate, UserRead
from app.security import create_access_token
from app.services.auth_service import (
    authenticate_google_user,
    authenticate_user,
    register_user,
)

router = APIRouter()


def _issue_token(user: User) -> Token:
    return Token(access_token=create_access_token(subject=str(user.user_id)))


@router.get("/config", response_model=AuthConfig)
async def auth_config() -> AuthConfig:
    """Expose non-secret auth config so the frontend follows the backend env."""
    return AuthConfig(
        google_enabled=bool(settings.google_client_id),
        google_client_id=settings.google_client_id,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Create a new account."""
    try:
        return await register_user(db, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=messages.already_registered(exc.field),
        )


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Exchange a username/email and password for a bearer token."""
    try:
        user = await authenticate_user(db, form_data.username, form_data.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages.CREDENTIALS_INVALID,
            headers=messages.AUTH_HEADER,
        )
    token = _issue_token(user)
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return token


@router.post("/google", response_model=Token)
async def google_login(
    response: Response,
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Exchange a Google ID token for a bearer token."""
    try:
        user = await authenticate_google_user(db, payload.credential)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    token = _issue_token(user)
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return token


@router.post("/logout")
async def logout(response: Response):
    """Clear the access_token cookie from the client browser."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user."""
    return current_user
