"""FastAPI router for authentication endpoints with HttpOnly cookies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from medai.auth.models import (
    AuthResult,
    ChangePasswordRequest,
    InvalidCredentialsError,
    IssuedTokens,
    LoginRequest,
    LoginTakenError,
    RegisterRequest,
    Role,
    RoleUpdateRequest,
    TooManyAttemptsError,
    UnauthorizedError,
    User,
    UserResponse,
)
from medai.auth.service import AuthService
from medai.config import AuthConfig

__all__ = ["create_auth_router", "get_current_user", "get_optional_user"]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def set_auth_cookies(
    response: Response, tokens: IssuedTokens, secure: bool = False
) -> None:
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


async def get_current_user(
    request: Request,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    auth_service: AuthService = request.app.state.auth_service
    token = access_token
    if not token:
        # Fallback to Authorization header if provided
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        user, _ = await auth_service.authenticate(token)
        return user
    except UnauthorizedError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        ) from err


async def get_optional_user(
    request: Request,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    auth_service: AuthService = request.app.state.auth_service
    token = access_token
    if not token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        return None
    try:
        user, _ = await auth_service.authenticate(token)
        return user
    except UnauthorizedError:
        return None


def create_auth_router(auth_service: AuthService, config: AuthConfig) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.post("/register", response_model=UserResponse)
    async def register(
        payload: RegisterRequest,
        request: Request,
        response: Response,
    ) -> UserResponse:
        ip = _get_client_ip(request)
        try:
            result: AuthResult = await auth_service.register(
                email=payload.email,
                password=payload.password,
                name=payload.name,
                ip=ip,
            )
            set_auth_cookies(response, result.tokens, secure=config.cookie_secure)
            return UserResponse(
                id=result.user.id,
                email=result.user.email,
                name=result.user.name,
                role=result.user.role,
                avatar_color=result.user.avatar_color,
            )
        except LoginTakenError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            ) from err
        except TooManyAttemptsError as err:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(err),
            ) from err

    @router.post("/login", response_model=UserResponse)
    async def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
    ) -> UserResponse:
        ip = _get_client_ip(request)
        try:
            result: AuthResult = await auth_service.login(
                email=payload.email,
                password=payload.password,
                ip=ip,
            )
            set_auth_cookies(response, result.tokens, secure=config.cookie_secure)
            return UserResponse(
                id=result.user.id,
                email=result.user.email,
                name=result.user.name,
                role=result.user.role,
                avatar_color=result.user.avatar_color,
            )
        except InvalidCredentialsError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            ) from err
        except TooManyAttemptsError as err:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(err),
            ) from err

    @router.post("/refresh", response_model=UserResponse)
    async def refresh(
        request: Request,
        response: Response,
        refresh_token: Annotated[str | None, Cookie()] = None,
    ) -> UserResponse:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing",
            )
        try:
            result: AuthResult = await auth_service.refresh(refresh_token=refresh_token)
            set_auth_cookies(response, result.tokens, secure=config.cookie_secure)
            return UserResponse(
                id=result.user.id,
                email=result.user.email,
                name=result.user.name,
                role=result.user.role,
                avatar_color=result.user.avatar_color,
            )
        except UnauthorizedError as err:
            clear_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            ) from err

    @router.post("/logout")
    async def logout(
        response: Response,
        refresh_token: Annotated[str | None, Cookie()] = None,
        access_token: Annotated[str | None, Cookie()] = None,
    ) -> dict[str, str]:
        await auth_service.logout(
            refresh_token=refresh_token, access_token=access_token
        )
        clear_auth_cookies(response)
        return {"status": "logged_out"}

    @router.post("/change-password")
    async def change_password(
        payload: ChangePasswordRequest,
        response: Response,
        user: User = Depends(get_current_user),
        access_token: Annotated[str | None, Cookie()] = None,
    ) -> dict[str, str]:
        jti: str | None = None
        if access_token:
            try:
                _, claims = await auth_service.authenticate(access_token)
                jti = claims.jti
            except UnauthorizedError:
                pass
        try:
            await auth_service.change_password(
                user_id=user.id,
                old_password=payload.old_password,
                new_password=payload.new_password,
                access_jti=jti,
                access_ttl_seconds=config.access_ttl_seconds,
            )
        except InvalidCredentialsError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Текущий пароль указан неверно.",
            )
        clear_auth_cookies(response)
        return {"status": "success", "message": "Пароль успешно обновлен"}

    @router.get("/me", response_model=UserResponse)
    async def me(user: User = Depends(get_current_user)) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            avatar_color=user.avatar_color,
        )

    @router.get("/admin/users", response_model=list[UserResponse])
    async def list_admin_users(
        user: User = Depends(get_current_user),
    ) -> list[UserResponse]:
        if user.role not in (Role.ADMIN, Role.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )
        all_users = await auth_service.list_users()
        return [
            UserResponse(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role,
                avatar_color=u.avatar_color,
            )
            for u in all_users
        ]

    @router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
    async def update_user_role(
        user_id: UUID,
        payload: RoleUpdateRequest,
        user: User = Depends(get_current_user),
    ) -> UserResponse:
        if user.role not in (Role.ADMIN, Role.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )
        if payload.role == Role.SUPERADMIN and user.role != Role.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can assign superadmin role",
            )
        all_users = await auth_service.list_users()
        target = next((u for u in all_users if u.id == user_id), None)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if target.role == Role.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify superadmin role",
            )
        updated = await auth_service.update_user_role(
            target_user_id=user_id, new_role=payload.role
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return UserResponse(
            id=updated.id,
            email=updated.email,
            name=updated.name,
            role=updated.role,
            avatar_color=updated.avatar_color,
        )

    return router
