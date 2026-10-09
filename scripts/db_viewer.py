"""Interactive PostgreSQL table and query viewer for EstateDB."""
from __future__ import annotations

import sys
from pathlib import Path
import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings


def get_connection():
    return psycopg.connect(settings.get_conninfo(), autocommit=True)


def show_tables():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_type = 'BASE TABLE'
                 ORDER BY table_name
                """
            )
            rows = cur.fetchall()
            print("\n--- Available Tables ---")
            for r in rows:
                table_name = r[0]
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                cnt = cur.fetchone()[0]
                print(f"  * {table_name:<25} ({cnt} rows)")
    finally:
        conn.close()


def query_table(table_name: str, limit: int = 20):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()

            col_widths = [len(c) for c in cols]
            for row in rows:
                for idx, val in enumerate(row):
                    col_widths[idx] = max(col_widths[idx], len(str(val) if val is not None else "NULL"))

            header = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cols))
            sep = "-+-".join("-" * col_widths[i] for i in range(len(cols)))

            print(f"\n--- {table_name.upper()} (first {len(rows)} rows) ---")
            print(header)
            print(sep)
            for row in rows:
                print(" | ".join(str(val if val is not None else "NULL").ljust(col_widths[i]) for i, val in enumerate(row)))
            print(f"\nTotal shown: {len(rows)}")
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
    finally:
        conn.close()


def run_custom_query(sql: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
                col_widths = [len(c) for c in cols]
                for row in rows:
                    for idx, val in enumerate(row):
                        col_widths[idx] = max(col_widths[idx], len(str(val) if val is not None else "NULL"))
                header = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cols))
                sep = "-+-".join("-" * col_widths[i] for i in range(len(cols)))
                print(f"\n{header}")
                print(sep)
                for row in rows:
                    print(" | ".join(str(val if val is not None else "NULL").ljust(col_widths[i]) for i, val in enumerate(row)))
                print(f"\nRows returned: {len(rows)}")
            else:
                conn.commit()
                print("Query executed successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() in ["--tables", "-t", "tables"]:
            show_tables()
        elif arg.lower().startswith("select") or arg.lower().startswith("show"):
            run_custom_query(" ".join(sys.argv[1:]))
        else:
            query_table(arg)
    else:
        try:
            show_tables()
        except Exception as exc:
            print(f"Cannot connect to PostgreSQL ({exc}). Ensure PostgreSQL is running.")
        print("\nUsage:")
        print("  python scripts/db_viewer.py                    # List all tables")
        print("  python scripts/db_viewer.py <table_name>       # View rows of a table (e.g. properties)")
        print("  python scripts/db_viewer.py \"SELECT ...\"       # Run any custom SQL query")
