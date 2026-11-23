"""Create an administrator or superadministrator account interactively.

Usage:
    python -m medai.create_admin --email admin@medai.ru [--role admin|superadmin] [--name 'Администратор']
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TextIO
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from medai.auth.models import Email, LoginTakenError, Password, Role
from medai.auth.passwords import Argon2PasswordHasher
from medai.auth.stores import UserStore
from medai.observability import log_event

__all__ = ["run"]

logger = logging.getLogger(__name__)


class _CreateAdminError(Exception):
    """Carries a safe message without passwords."""


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m medai.create_admin",
        description="Создать учетную запись администратора MedAI.",
    )
    parser.add_argument("--email", required=True, help="Email администратора")
    parser.add_argument(
        "--role",
        default="admin",
        choices=["admin", "superadmin"],
        help="Роль учетной записи (admin или superadmin)",
    )
    parser.add_argument(
        "--name",
        default="Администратор MedAI",
        help="Отображаемое имя пользователя",
    )
    return parser.parse_args(argv)


async def run(
    argv: Sequence[str],
    *,
    users: UserStore,
    hasher: Argon2PasswordHasher,
    read_password: Callable[[str], str] = getpass.getpass,
    output: TextIO = sys.stdout,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    args = _parse_args(argv)
    try:
        try:
            validated_email = TypeAdapter(Email).validate_python(args.email)
        except ValidationError as err:
            raise _CreateAdminError("Некорректный формат email.") from err

        password = read_password("Введите пароль: ")
        confirm = read_password("Повторите пароль: ")
        if password != confirm:
            raise _CreateAdminError("Введенные пароли не совпадают.")

        try:
            TypeAdapter(Password).validate_python(password)
        except ValidationError as err:
            raise _CreateAdminError(
                "Пароль должен содержать от 6 до 128 символов."
            ) from err

        password_hash = await hasher.hash(password)
        role = Role(args.role)
        now = clock()

        try:
            user = await users.create(
                id=uuid4(),
                email=validated_email,
                name=args.name,
                password_hash=password_hash,
                role=role,
                avatar_color="#059669" if role == Role.SUPERADMIN else "#2563EB",
                now=now,
            )
        except LoginTakenError as err:
            raise _CreateAdminError(
                f"Пользователь с email «{validated_email}» уже зарегистрирован."
            ) from err

    except _CreateAdminError as err:
        print(f"Ошибка: {err}", file=output)
        return 1

    log_event(logger, logging.INFO, "auth.admin.created", user_id=str(user.id))
    print(
        f"Пользователь «{user.name}» с ролью «{user.role.value}» ({user.email}) успешно создан.",
        file=output,
    )
    return 0


async def _main(argv: Sequence[str]) -> int:
    from medai.auth.postgres import PostgresUserStore
    from medai.config import load_config
    from medai.db.engine import create_engine

    config = load_config()
    engine = create_engine(config.database)
    try:
        user_store = PostgresUserStore(engine)
        hasher = Argon2PasswordHasher()
        return await run(argv, users=user_store, hasher=hasher)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(sys.argv[1:])))
