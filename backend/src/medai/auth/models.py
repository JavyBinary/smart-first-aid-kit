"""Domain models, contracts, and exceptions for MedAI authentication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

__all__ = [
    "AccessClaims",
    "AuthError",
    "AuthResult",
    "AuthUnavailableError",
    "Credentials",
    "Email",
    "ForbiddenError",
    "InvalidCredentialsError",
    "IssuedTokens",
    "LoginRequest",
    "LoginTakenError",
    "Password",
    "RefreshSession",
    "RegisterRequest",
    "Role",
    "TooManyAttemptsError",
    "UnauthorizedError",
    "User",
    "UserResponse",
    "UserWithPassword",
]

EMAIL_PATTERN = r"^[^@]+@[^@]+\.[^@]+$"

Email = Annotated[str, StringConstraints(pattern=EMAIL_PATTERN, to_lower=True)]
Password = Annotated[str, StringConstraints(min_length=6, max_length=128)]


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    email: Email
    password: Password
    name: str = Field(default="Пользователь", min_length=1, max_length=64)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    email: Email
    password: Password


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    old_password: Password
    new_password: Password


class RoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Role


class UpdateMeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=64)
    avatar_color: str | None = Field(default=None, min_length=1, max_length=32)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    email: Email
    password: Password


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    email: str
    name: str
    role: Role
    avatar_color: str


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    name: str
    role: Role
    avatar_color: str


@dataclass(frozen=True, slots=True)
class UserWithPassword:
    user: User
    password_hash: str


@dataclass(frozen=True, slots=True)
class RefreshSession:
    id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: bytes
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    role: Role
    jti: str
    session_id: UUID
    family_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    tokens: IssuedTokens


class AuthError(Exception):
    """Base class for safe authentication errors without request details."""


class LoginTakenError(AuthError):
    def __init__(self) -> None:
        super().__init__("Email is already registered.")


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class UnauthorizedError(AuthError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)


class ForbiddenError(AuthError):
    def __init__(self) -> None:
        super().__init__("Forbidden: insufficient permissions.")


class AuthUnavailableError(AuthError):
    def __init__(self) -> None:
        super().__init__("Authentication storage is unavailable.")


class TooManyAttemptsError(AuthError):
    """A rate limit was hit; retry_after indicates wait time in seconds."""

    def __init__(self, limit: str, retry_after: int) -> None:
        super().__init__("Too many attempts. Please try again later.")
        self.limit = limit
        self.retry_after = retry_after
