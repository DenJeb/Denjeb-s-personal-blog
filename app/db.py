"""
========== 数据库连接 ==========
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings
from app.time_utils import mysql_timezone_offset

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,  # 想看 SQL 时改成 True
)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

elif engine.dialect.name in {"mysql", "mariadb"}:

    @event.listens_for(engine, "connect")
    def _set_mysql_session_timezone(dbapi_connection, _connection_record):
        # 让 NOW() 和 CURRENT_TIMESTAMP 使用站点时区，而不是服务器默认时区。
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET time_zone = '{mysql_timezone_offset()}'")
        finally:
            cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
