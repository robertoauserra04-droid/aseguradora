import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool
from app.config.env import DATABASE_URL, NODE_ENV

_connect_args = {}
if NODE_ENV == "production":
    _connect_args["sslmode"] = "require"

_pool = pg_pool.SimpleConnectionPool(
    1, 20,
    DATABASE_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
    **_connect_args,
)


class QueryResult:
    def __init__(self, rows, rowcount):
        self.rows = rows
        self.rowcount = rowcount


def query(sql: str, params: list = None) -> QueryResult:
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            conn.commit()
            try:
                rows = [dict(r) for r in cur.fetchall()]
            except Exception:
                rows = []
            return QueryResult(rows=rows, rowcount=cur.rowcount)
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
