"""Authentication HTTP endpoints: register, login, and current-user lookup.

These handlers are intentionally thin. They validate input via Pydantic schemas,
delegate all logic to ``auth_service``, and translate the service's domain
exceptions into HTTP responses. No business rules live here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.google_oauth import GoogleAuthError
from app.models.user import User
from app.schemas.auth import AuthConfig, GoogleAuthRequest, Token, UserCreate, UserRead
from app.security import create_access_token
from app.services.auth_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    authenticate_google_user,
    authenticate_user,
    register_user,
)

router = APIRouter()


@router.get("/config", response_model=AuthConfig)
async def auth_config() -> AuthConfig:
    """Expose non-secret auth configuration (the Google client id) to the frontend.

    Lets the browser decide whether to render "Continue with Google" without
    hardcoding the client id, keeping the backend ``.env`` the single source.
    """
    return AuthConfig(
        google_enabled=bool(settings.google_client_id),
        google_client_id=settings.google_client_id,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new account and return the created user.

    Returns 201 with the public user representation on success, or 409 if the
    chosen username or email is already taken.
    """
    try:
        return await register_user(db, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"That {exc.field} is already registered.",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Exchange credentials for a bearer access token.

    Accepts the standard OAuth2 password form (``username`` + ``password``),
    where ``username`` may be either the account's email or username. This makes
    both the Swagger "Authorize" button and the web frontend work unchanged.
    Returns 401 on any credential mismatch.
    """
    try:
        user = await authenticate_user(db, form_data.username, form_data.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=str(user.user_id))
    return Token(access_token=access_token)


@router.post("/google", response_model=Token)
async def google_login(payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Sign in (or sign up) with a Google ID token and return our bearer token.

    Accepts the credential issued by Google Identity Services in the browser,
    verifies it server-side, then finds, links, or creates the matching local
    account and mints an access token — identical in shape to ``/login`` so the
    frontend stores and uses it the same way. Returns 401 if the credential is
    invalid or Google sign-in is not configured.
    """
    try:
        user = await authenticate_google_user(db, payload.credential)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    access_token = create_access_token(subject=str(user.user_id))
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the profile of the authenticated user (identified by the bearer token)."""
    return current_user
