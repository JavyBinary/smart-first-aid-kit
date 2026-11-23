"""Authentication module for MedAI."""

from medai.auth.models import (
    AccessClaims,
    AuthError,
    AuthResult,
    Credentials,
    InvalidCredentialsError,
    IssuedTokens,
    LoginRequest,
    LoginTakenError,
    RefreshSession,
    RegisterRequest,
    Role,
    TooManyAttemptsError,
    UnauthorizedError,
    User,
    UserResponse,
    UserWithPassword,
)
from medai.auth.passwords import Argon2PasswordHasher
from medai.auth.postgres import PostgresSessionStore, PostgresUserStore
from medai.auth.rate_limiter import InMemoryRateLimiter, RateLimiter
from medai.auth.router import create_auth_router, get_current_user
from medai.auth.service import AuthService
from medai.auth.stores import SessionStore, UserStore
from medai.auth.tokens import TokenCodec, hash_refresh_token, new_refresh_token

__all__ = [
    "AccessClaims",
    "Argon2PasswordHasher",
    "AuthError",
    "AuthResult",
    "AuthService",
    "Credentials",
    "InMemoryRateLimiter",
    "InvalidCredentialsError",
    "IssuedTokens",
    "LoginRequest",
    "LoginTakenError",
    "PostgresSessionStore",
    "PostgresUserStore",
    "RateLimiter",
    "RefreshSession",
    "RegisterRequest",
    "Role",
    "SessionStore",
    "TokenCodec",
    "TooManyAttemptsError",
    "UnauthorizedError",
    "User",
    "UserResponse",
    "UserStore",
    "UserWithPassword",
    "create_auth_router",
    "get_current_user",
    "hash_refresh_token",
    "new_refresh_token",
]
