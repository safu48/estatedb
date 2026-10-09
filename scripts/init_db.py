"""Build the EstateDB schema from Python for PostgreSQL.

    python scripts/init_db.py             # run 01_drop .. 06_seed in order
    python scripts/init_db.py 03 05       # re-run only those numbered files
    python scripts/init_db.py --no-seed   # schema only, no demo data
    python scripts/init_db.py --list      # show what would run, then stop

Equivalent to running ``sql/run_all.sql`` in psql or pgAdmin.
It connects using configuration from ``.env`` or DATABASE_URL.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow "python scripts/init_db.py" from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402
from psycopg import errors  # noqa: E402

from app.config import settings  # noqa: E402

SQL_DIR = PROJECT_ROOT / "sql"

SCRIPTS = [
    ("01_drop.sql",       "Drop any existing objects"),
    ("02_tables.sql",     "Tables, constraints, indexes"),
    ("03_triggers.sql",   "Audit and business logic triggers"),
    ("04_views.sql",      "Reporting and KPI views"),
    ("05_procedures.sql", "Stored functions and procedures"),
    ("06_seed.sql",       "Seed data"),
]


# ---------------------------------------------------------------------------
#  Running one script
# ---------------------------------------------------------------------------
def first_line(statement: str) -> str:
    """A short label for a statement, for progress and error messages."""
    for line in statement.splitlines():
        line = line.strip()
        if line and not line.startswith("--") and not line.startswith("#"):
            return line[:88]
    return statement[:88]


def run_script(conn: psycopg.Connection, path: Path) -> list[tuple[str, str]]:
    """Execute SQL script file. Returns a list of (label, error)."""
    script_text = path.read_text(encoding="utf-8")
    failures: list[tuple[str, str]] = []

    try:
        with conn.cursor() as cur:
            cur.execute(script_text)
        conn.commit()
        print(f"      executed {path.name} successfully")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        failures.append((first_line(script_text), str(exc).strip()))

    return failures


# ---------------------------------------------------------------------------
#  Verification
# ---------------------------------------------------------------------------
EXPECTED = {
    "BASE TABLE": 14,
    "VIEW": 4,
    "TRIGGER": 9,
    "PROCEDURE": 1,
    "FUNCTION": 4,
}


def verify(conn: psycopg.Connection) -> bool:
    """Read the PostgreSQL data dictionary back and report on it."""
    healthy = True

    with conn.cursor() as cur:
        print("\n--- Objects created " + "-" * 40)

        # Tables
        cur.execute(
            """
            SELECT COUNT(*)
              FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_type = 'BASE TABLE'
            """
        )
        row = cur.fetchone()
        table_count = row[0] if row else 0
        note = "  ok" if table_count == EXPECTED["BASE TABLE"] else f"  EXPECTED {EXPECTED['BASE TABLE']}"
        if table_count != EXPECTED["BASE TABLE"]:
            healthy = False
        print(f"  {'TABLE':<14} {table_count:>3}{note}")

        # Views
        cur.execute(
            """
            SELECT COUNT(*)
              FROM information_schema.views
             WHERE table_schema = 'public'
            """
        )
        row = cur.fetchone()
        view_count = row[0] if row else 0
        note = "  ok" if view_count == EXPECTED["VIEW"] else f"  EXPECTED {EXPECTED['VIEW']}"
        if view_count != EXPECTED["VIEW"]:
            healthy = False
        print(f"  {'VIEW':<14} {view_count:>3}{note}")

        # Triggers
        cur.execute(
            """
            SELECT COUNT(*)
              FROM information_schema.triggers
             WHERE trigger_schema = 'public'
            """
        )
        row = cur.fetchone()
        trigger_count = row[0] if row else 0
        note = "  ok" if trigger_count >= EXPECTED["TRIGGER"] else f"  EXPECTED >= {EXPECTED['TRIGGER']}"
        if trigger_count < EXPECTED["TRIGGER"]:
            healthy = False
        print(f"  {'TRIGGER':<14} {trigger_count:>3}{note}")

        # Routines: Procedure and Function
        cur.execute(
            """
            SELECT routine_type, COUNT(*)
              FROM information_schema.routines
             WHERE routine_schema = 'public'
             GROUP BY routine_type
            """
        )
        routines = {r[0]: r[1] for r in cur.fetchall()}
        for r_type in ("PROCEDURE", "FUNCTION"):
            cnt = routines.get(r_type, 0)
            exp = EXPECTED[r_type]
            note = "  ok" if cnt >= exp else f"  EXPECTED >= {exp}"
            if cnt < exp:
                healthy = False
            print(f"  {r_type:<14} {cnt:>3}{note}")

        print("\n--- Row counts " + "-" * 45)
        for table in ("roles", "cities", "property_types", "amenities", "users",
                      "agents", "properties", "property_images",
                      "property_amenities", "inquiries", "transactions",
                      "reviews", "favorites", "audit_log"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                r = cur.fetchone()
                print(f"  {table:<20} {r[0] if r else 0:>5}")
            except Exception as exc:  # noqa: BLE001
                healthy = False
                print(f"  {table:<20} -- {str(exc).strip()}")

    return healthy


# ---------------------------------------------------------------------------
#  Connection Helper
# ---------------------------------------------------------------------------
def connect_database() -> psycopg.Connection:
    """Connect to PostgreSQL, auto-creating the database schema if needed."""
    conninfo = settings.get_conninfo()
    try:
        return psycopg.connect(conninfo, autocommit=False)
    except (errors.InvalidCatalogName, psycopg.OperationalError) as exc:
        # If database does not exist locally, attempt creating it via admin DB
        if "database" in str(exc).lower() and "does not exist" in str(exc).lower():
            print(f"Database '{settings.DB_NAME}' does not exist yet. Creating it...")
            admin_conninfo = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
            if settings.DB_SSL:
                admin_conninfo += "?sslmode=require"
            with psycopg.connect(admin_conninfo, autocommit=True) as admin_conn:
                with admin_conn.cursor() as cur:
                    cur.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
            return psycopg.connect(conninfo, autocommit=False)
        raise


def auto_init_if_needed() -> bool:
    """Check if the tables exist; if not, automatically initialize the schema and seed data."""
    try:
        conn = connect_database()
    except Exception as exc:
        print(f"Auto-init: Could not connect to database ({exc}).")
        return False

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'roles'
                """
            )
            exists = cur.fetchone()[0] > 0

        if exists:
            return True

        print("Auto-init: Database tables not found. Initializing schema and seed data...")
        for name, label in SCRIPTS:
            print(f"  Running {name} ({label})...")
            run_script(conn, SQL_DIR / name)

        verify(conn)
        print("Auto-init: Completed successfully!")
        return True


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------
def chosen_scripts(argv: list[str]) -> list[tuple[str, str]]:
    """Work out which files to run from the command line arguments."""
    wanted = [a for a in argv if not a.startswith("-")]
    scripts = list(SCRIPTS)

    if wanted:
        picked = []
        for token in wanted:
            key = token if token.endswith(".sql") else None
            for name, label in SCRIPTS:
                if name == key or name.startswith(token.zfill(2) + "_"):
                    picked.append((name, label))
                    break
            else:
                sys.exit(f"No script matches '{token}'. "
                         f"Choose from: {', '.join(n for n, _ in SCRIPTS)}")
        scripts = picked
    elif "--no-seed" in argv:
        scripts = [s for s in SCRIPTS if s[0] != "06_seed.sql"]

    return scripts


def main(argv: list[str]) -> int:
    scripts = chosen_scripts(argv)

    print("=" * 62)
    print("  EstateDB schema build (PostgreSQL / Render)")
    print("=" * 62)
    print(f"  host    : {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  user    : {settings.DB_USER}")
    print(f"  database: {settings.DB_NAME}")
    print(f"  scripts : {', '.join(name for name, _ in scripts)}")

    missing = [name for name, _ in scripts if not (SQL_DIR / name).exists()]
    if missing:
        sys.exit(f"\nMissing from {SQL_DIR}: {', '.join(missing)}")

    if "--list" in argv:
        print("\n--list given, nothing executed.")
        return 0

    try:
        conn = connect_database()
    except Exception as exc:
        print(f"\nCould not connect to PostgreSQL:\n  {str(exc).strip()}")
        print("\nTroubleshooting tips:")
        print(f"  -> Check DATABASE_URL or DB_HOST '{settings.DB_HOST}' / port '{settings.DB_PORT}'.")
        print("  -> For Render, copy the Internal (or External) Database URL into DATABASE_URL.")
        print("  -> For local PostgreSQL, ensure the PostgreSQL service is started.")
        return 2

    all_failures: list[tuple[str, str, str]] = []
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            server_version = cur.fetchone()[0]
        print(f"\nConnected to PostgreSQL server:\n  {server_version}\n")

        for index, (name, label) in enumerate(scripts, start=1):
            print(f"[{index}/{len(scripts)}] {name} -- {label}")
            for statement, error in run_script(conn, SQL_DIR / name):
                all_failures.append((name, statement, error))

        healthy = verify(conn)

    print("\n" + "=" * 62)
    if all_failures:
        print(f"  {len(all_failures)} script(s) failed:")
        for name, statement, error in all_failures:
            print(f"\n  {name}: {statement}")
            for line in error.splitlines():
                print(f"      {line}")
    else:
        print("  Every statement ran without error.")

    if healthy and not all_failures:
        print("\n  Build looks good! Start the app with:  python run.py")
        print("=" * 62)
        return 0

    print("\n  Build finished with problems -- see above.")
    print("=" * 62)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
