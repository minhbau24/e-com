"""Database connection helpers."""

from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from core.config import settings


class DatabaseError(RuntimeError):
    """Raised when the search database cannot be accessed."""


@contextmanager
def get_connection():
    if not settings.POSTGRES_URL:
        raise DatabaseError("POSTGRES_URL is not configured")

    conn = psycopg2.connect(settings.POSTGRES_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
