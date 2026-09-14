"""PostgreSQL 연결 헬퍼.

.env의 DATABASE_URL을 읽어 psycopg로 연결.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


def _load_env_file() -> None:
    """의존성 최소화를 위한 미니 .env 로더."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file()


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Create .env with DATABASE_URL=postgresql://..."
        )
    return url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        yield conn