import re
from contextlib import contextmanager
from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

CLIENT_MODE: str = "PostgreSQL (psycopg3)"
CLIENT_WARNING: Optional[str] = None
STARTUP_ERROR: Optional[str] = None

_pool: Optional[ConnectionPool] = None


def init_pool() -> None:
    """Create the PostgreSQL connection pool and test connection."""
    global _pool, STARTUP_ERROR
    conninfo = settings.get_conninfo()
    try:
        # Quick direct connection check with short timeout
        with psycopg.connect(conninfo, connect_timeout=4, autocommit=True) as test_conn:
            with test_conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        # If direct check succeeded, initialize pool
        pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "autocommit": False},
        )
        _pool = pool
        STARTUP_ERROR = None
    except Exception as exc:  # noqa: BLE001
        _pool = None
        STARTUP_ERROR = str(exc)


def close_pool() -> None:
    """Tear down pool on shutdown."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError(
            f"Database is not connected. Make sure PostgreSQL is accessible at {settings.DB_HOST}:{settings.DB_PORT} "
            f"and database '{settings.DB_NAME}' exists. Details: {STARTUP_ERROR or 'n/a'}"
        )
    return _pool


@contextmanager
def get_connection():
    """Borrow a pooled connection (returned automatically on exit)."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


@contextmanager
def transaction():
    """Run several statements atomically in a transaction block."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.transaction():
            yield conn


def _prepare_sql_and_params(sql: str, params: Optional[dict] = None) -> tuple[str, Optional[dict]]:
    """Convert :param placeholders to %(param)s and escape literal % characters."""
    if not params:
        return sql, None

    # Replace :param with %(param)s (when preceded by whitespace, comma, paren, operator, or start of line)
    converted = re.sub(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)", r"%(\1)s", sql)
    # Double any % that is not followed by (param_name)s or % (e.g. LIKE '%...', TO_CHAR)
    converted = re.sub(r"%(?!\([a-zA-Z0-9_]+\)s|%)", "%%", converted)
    return converted, params


# ---------------------------------------------------------------------------
#  Query helpers
# ---------------------------------------------------------------------------
def query(sql: str, params: Optional[dict] = None) -> list[dict]:
    """Run a SELECT and return every row as a dict."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            prep_sql, prep_params = _prepare_sql_and_params(sql, params)
            if prep_params:
                cur.execute(prep_sql, prep_params)
            else:
                cur.execute(prep_sql)
            return cur.fetchall()


def query_one(sql: str, params: Optional[dict] = None) -> Optional[dict]:
    """Run a SELECT and return the first row (or None)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            prep_sql, prep_params = _prepare_sql_and_params(sql, params)
            if prep_params:
                cur.execute(prep_sql, prep_params)
            else:
                cur.execute(prep_sql)
            return cur.fetchone()


def scalar(sql: str, params: Optional[dict] = None) -> Any:
    """Return the first column of the first row (or None)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            prep_sql, prep_params = _prepare_sql_and_params(sql, params)
            if prep_params:
                cur.execute(prep_sql, prep_params)
            else:
                cur.execute(prep_sql)
            row = cur.fetchone()
            if not row:
                return None
            return next(iter(row.values()))


def execute(sql: str, params: Optional[dict] = None) -> int:
    """Run one INSERT/UPDATE/DELETE and COMMIT. Returns affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            prep_sql, prep_params = _prepare_sql_and_params(sql, params)
            if prep_params:
                cur.execute(prep_sql, prep_params)
            else:
                cur.execute(prep_sql)
            conn.commit()
            return cur.rowcount


def insert_returning_id(sql: str, params: Optional[dict] = None, out_key: str = "new_id") -> int:
    """Run an INSERT and return the primary key."""
    clean_sql = sql.strip().rstrip(";")
    # Strip any MySQL RETURNING INTO clause if present
    clean_sql = re.sub(r"\s+RETURNING\s+[a-zA-Z0-9_]+\s+INTO\s+:[a-zA-Z0-9_]+", "", clean_sql, flags=re.IGNORECASE)
    # If sql doesn't already have RETURNING, append RETURNING *
    if "RETURNING" not in clean_sql.upper():
        clean_sql = f"{clean_sql} RETURNING *"

    clean_params = {k: v for k, v in (params or {}).items() if k != out_key}
    with get_connection() as conn:
        with conn.cursor() as cur:
            prep_sql, prep_params = _prepare_sql_and_params(clean_sql, clean_params)
            if prep_params:
                cur.execute(prep_sql, prep_params)
            else:
                cur.execute(prep_sql)
            row = cur.fetchone()
            conn.commit()
            if not row:
                return 0
            if out_key in row:
                return int(row[out_key])
            # Return first column (primary key in EstateDB tables)
            return int(next(iter(row.values())))


# ---------------------------------------------------------------------------
#  Stored procedure / function callers
# ---------------------------------------------------------------------------
def call_record_sale(property_id: int, buyer_id: int,
                     sale_price: float, txn_type: str) -> int:
    """Invoke sp_record_sale and return the new transaction id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_record_sale(%(pid)s, %(bid)s, %(price)s, %(ttype)s) AS txn_id",
                {"pid": property_id, "bid": buyer_id, "price": sale_price, "ttype": txn_type},
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["txn_id"]) if row and row.get("txn_id") is not None else None


def call_update_inquiry_status(inquiry_id: int, status: str) -> None:
    """Invoke the sp_update_inquiry_status procedure."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CALL sp_update_inquiry_status(%(iid)s, %(status)s)",
                {"iid": inquiry_id, "status": status},
            )
            conn.commit()


def call_months_listed(property_id: int) -> Optional[float]:
    """Invoke the fn_months_listed function."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT fn_months_listed(%(pid)s) AS months", {"pid": property_id})
            row = cur.fetchone()
            if not row or row.get("months") is None:
                return None
            return float(row["months"])
