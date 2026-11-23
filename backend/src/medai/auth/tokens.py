"""JWT and cryptographically secure refresh token handling for MedAI."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from medai.auth.models import AccessClaims, Role, UnauthorizedError
from medai.config import AuthConfig

__all__ = [
    "TokenCodec",
    "hash_refresh_token",
    "new_refresh_token",
]

_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ["sub", "role", "jti", "sid", "fid", "iat", "exp", "iss"]


class TokenCodec:
    def __init__(self, config: AuthConfig, issuer: str = "medai-backend") -> None:
        self._secret = config.jwt_secret
        self._issuer = issuer
        self._access_ttl = timedelta(seconds=config.access_ttl_seconds)

    def encode_access(
        self,
        user_id: UUID,
        role: Role,
        session_id: UUID,
        family_id: UUID,
        now: datetime,
    ) -> tuple[str, AccessClaims]:
        issued_at = now.replace(microsecond=0)
        claims = AccessClaims(
            user_id=user_id,
            role=role,
            jti=uuid4().hex,
            session_id=session_id,
            family_id=family_id,
            issued_at=issued_at,
            expires_at=issued_at + self._access_ttl,
        )
        payload = {
            "sub": str(claims.user_id),
            "role": claims.role.value,
            "jti": claims.jti,
            "sid": str(claims.session_id),
            "fid": str(claims.family_id),
            "iat": int(claims.issued_at.timestamp()),
            "exp": int(claims.expires_at.timestamp()),
            "iss": self._issuer,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM), claims

    def decode_access(
        self,
        token: str,
        now: datetime,
        *,
        verify_expiry: bool = True,
    ) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],
                issuer=self._issuer,
                options={
                    "require": _REQUIRED_CLAIMS,
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
            claims = AccessClaims(
                user_id=UUID(payload["sub"]),
                role=Role(payload["role"]),
                jti=str(payload["jti"]),
                session_id=UUID(payload["sid"]),
                family_id=UUID(payload["fid"]),
                issued_at=datetime.fromtimestamp(int(payload["iat"]), UTC),
                expires_at=datetime.fromtimestamp(int(payload["exp"]), UTC),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise UnauthorizedError from error

        if verify_expiry and claims.expires_at <= now:
            raise UnauthorizedError("Token expired")
        return claims


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()
