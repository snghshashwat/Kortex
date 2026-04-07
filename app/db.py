from contextlib import contextmanager
from typing import Generator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

# A small shared connection pool keeps costs and latency low on free tiers.
pool = ConnectionPool(conninfo=settings.database_url, min_size=1, max_size=5, open=False)


def open_pool() -> None:
    pool.open()


def close_pool() -> None:
    pool.close()


@contextmanager
def get_db() -> Generator:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield conn, cur
