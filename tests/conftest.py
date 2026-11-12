"""
========== pytest 共享 fixture ==========
"""

import os
import re
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, delete, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import PROJECT_DIR, settings

TEST_ADMIN_EMAIL = "__pytest_admin@example.com"

# 测试库：优先 TEST_DATABASE_URL；未配置时使用独立的 SQLite 文件。
# 必须在导入 app.db / app.main 之前替换，否则 engine 会连到开发库。
_configured_test_url = settings.test_database_url or os.environ.get(
    "TEST_DATABASE_URL", ""
)
if _configured_test_url:
    _test_url = make_url(_configured_test_url)
else:
    _sqlite_path = PROJECT_DIR / ".pytest-blog.db"
    _test_url = make_url(f"sqlite:///{_sqlite_path.as_posix()}")

if _test_url.get_backend_name() == "sqlite":
    if "test" not in Path(_test_url.database or "").name.lower():
        raise RuntimeError("SQLite 测试库文件名需要包含 test，避免误用正式库。")
elif not _test_url.database or not _test_url.database.endswith("_test"):
    raise RuntimeError(
        f"MySQL 测试库名必须以 _test 结尾，避免误连开发库：{_test_url.database!r}"
    )

_test_url_string = _test_url.render_as_string(hide_password=False)
settings.database_url = _test_url_string
settings.admin_email = TEST_ADMIN_EMAIL
settings.email_enabled = False
settings.admin_login_code_enabled = True
settings.legacy_public_site_enabled = True
os.environ["DATABASE_URL"] = _test_url_string

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    AdminUser,
    EmailRegistrationBlock,
    Message,
    Moment,
    MomentComment,
    NotificationOutbox,
    RateLimitEvent,
    User,
    VerificationCode,
)
from app.services import accounts as accounts_service  # noqa: E402
from tests.utils import csrf_token  # noqa: E402

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _register_sqlite_functions(dbapi_connection, _connection_record):
        import json as json_module

        def json_contains(document, value):
            try:
                return int(json_module.loads(value) in json_module.loads(document))
            except (TypeError, ValueError):
                return 0

        dbapi_connection.create_function("json_contains", 2, json_contains)
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


ADMIN_USERNAME = "__pytest_admin__"
ADMIN_EMAIL = TEST_ADMIN_EMAIL
ADMIN_PASSWORD = "PytestPass123!"
USER_EMAIL = "__pytest_user@example.com"
USER_NICKNAME = "__pytest_user__"
USER_PASSWORD = "UserPass123!"


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Generator[None]:
    """每次测试会话都从空库执行迁移，并灌入样例内容。"""
    from alembic import command
    from alembic.config import Config

    if engine.dialect.name != "sqlite":
        database = _test_url.database
        assert database is not None
        if re.fullmatch(r"[A-Za-z0-9_]+", database) is None:
            raise RuntimeError(f"测试库名不合法：{database!r}")

        server_engine = create_engine(
            _test_url._replace(database=None),
            pool_pre_ping=True,
        )
        try:
            with server_engine.connect() as connection:
                exists = connection.execute(
                    text(
                        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                        "WHERE SCHEMA_NAME = :name"
                    ),
                    {"name": database},
                ).first()
                if exists is None:
                    connection.execute(
                        text(
                            f"CREATE DATABASE `{database}` "
                            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                        )
                    )
                    connection.commit()
        except OperationalError as exc:
            raise RuntimeError(
                f"无法创建或访问测试库 {database}。请用 MySQL 管理员执行：\n"
                f"  CREATE DATABASE `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;\n"
                f"  GRANT ALL PRIVILEGES ON `{database}`.* "
                "TO '<数据库用户>'@'localhost';\n"
                "或把 TEST_DATABASE_URL 指向已有测试库。"
            ) from exc
        finally:
            server_engine.dispose()

    # 清空测试库，模拟全新数据库
    with engine.begin() as connection:
        if engine.dialect.name != "sqlite":
            connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        # 已移除的笔记/分类表不在当前 metadata 中，需要单独清理
        connection.execute(text("DROP TABLE IF EXISTS `notes`"))
        connection.execute(text("DROP TABLE IF EXISTS `categories`"))
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(text(f"DROP TABLE IF EXISTS `{table.name}`"))
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        if engine.dialect.name != "sqlite":
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    alembic_cfg = Config(str(PROJECT_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    from app.seed import seed

    seed()
    yield


@pytest.fixture(autouse=True)
def reset_transient_state() -> Generator[None]:
    with SessionLocal() as db:
        db.execute(delete(VerificationCode))
        db.execute(delete(EmailRegistrationBlock))
        db.execute(delete(RateLimitEvent))
        db.execute(delete(NotificationOutbox))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(VerificationCode))
        db.execute(delete(EmailRegistrationBlock))
        db.execute(delete(RateLimitEvent))
        db.execute(delete(NotificationOutbox))
        db.commit()


@pytest.fixture(autouse=True)
def reset_new_content() -> Generator[None]:
    with SessionLocal() as db:
        db.execute(delete(MomentComment))
        db.execute(delete(Moment))
        db.execute(delete(Message))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(MomentComment))
        db.execute(delete(Moment))
        db.execute(delete(Message))
        db.commit()


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_client(monkeypatch) -> Generator[TestClient]:
    monkeypatch.setattr(accounts_service, "generate_code", lambda: "123456")
    monkeypatch.setattr(accounts_service, "send_code", lambda *args, **kwargs: True)

    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == USER_EMAIL))
        db.execute(delete(User).where(User.username == USER_NICKNAME))
        db.commit()

    try:
        with TestClient(app) as test_client:
            register_page = test_client.get("/register")
            token = csrf_token(register_page.text)
            response = test_client.post(
                "/register",
                data={
                    "csrf_token": token,
                    "email": USER_EMAIL,
                    "nickname": USER_NICKNAME,
                    "password": USER_PASSWORD,
                    "confirm": USER_PASSWORD,
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == "/register/verify"

            verify_page = test_client.get("/register/verify")
            token = csrf_token(verify_page.text)
            response = test_client.post(
                "/register/verify",
                data={"csrf_token": token, "code": "123456"},
                follow_redirects=False,
            )
            assert response.status_code == 303
            yield test_client
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email == USER_EMAIL))
            db.execute(delete(User).where(User.username == USER_NICKNAME))
            db.commit()


@pytest.fixture
def admin_client(monkeypatch) -> Generator[TestClient]:
    monkeypatch.setattr(accounts_service, "generate_code", lambda: "123456")
    monkeypatch.setattr(accounts_service, "send_code", lambda *args, **kwargs: True)

    with SessionLocal() as db:
        db.execute(delete(AdminUser).where(AdminUser.username == ADMIN_USERNAME))
        db.add(
            AdminUser(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=PasswordHash.recommended().hash(ADMIN_PASSWORD),
            )
        )
        db.commit()

    try:
        with TestClient(app) as test_client:
            login_page = test_client.get("/admin/login")
            token = csrf_token(login_page.text)
            response = test_client.post(
                "/admin/login",
                data={
                    "username": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                    "csrf_token": token,
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == "/admin/login/code"

            code_page = test_client.get("/admin/login/code")
            token = csrf_token(code_page.text)
            response = test_client.post(
                "/admin/login/code",
                data={"csrf_token": token, "code": "123456"},
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == "/admin/"
            yield test_client
    finally:
        with SessionLocal() as db:
            db.execute(delete(AdminUser).where(AdminUser.username == ADMIN_USERNAME))
            db.commit()
