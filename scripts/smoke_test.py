"""Boot the application in-process and request every route.

    python scripts/smoke_test.py

This is the strongest check that can be made without a MySQL server. It does
not need one: with no database reachable the start-up hook records the failure
and the ``database_guard`` middleware answers every page with ``db_error.html``,
so a 200 proves the whole chain works -- routing, sessions, the middleware, the
template environment and every filter -- without a single row being read.

If MySQL *is* reachable, the same run becomes a real end-to-end test: it logs
in as each demo user and requests their pages with a live session, so a broken
query or a template referencing a column that does not exist shows up here
rather than in front of a marker. The output says which mode it ran in.

Requires httpx (see requirements-dev.txt). A non-zero exit means something
returned 500 or raised.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    sys.exit("This check needs httpx:  pip install -r requirements-dev.txt")

from app import database as db          # noqa: E402
from app.main import app                # noqa: E402

# Every GET page, grouped by the role that may see it.  POST routes are left
# alone on purpose: this check must not write to a database it did not create.
PUBLIC_PAGES = [
    "/", "/listings", "/listings?city_id=1&sort=price_asc", "/listings?page=2",
    "/agents", "/agents/2", "/market", "/property/1", "/login", "/register",
]
CUSTOMER_PAGES = [
    "/me", "/me/favorites", "/me/inquiries", "/me/reviews", "/me/profile",
]
AGENT_PAGES = [
    "/agent", "/agent/properties", "/agent/properties/new", "/agent/inquiries",
    "/agent/sales", "/agent/profile",
]
ADMIN_PAGES = [
    "/admin", "/admin/users", "/admin/agents/new", "/admin/properties",
    "/admin/properties?status=SOLD", "/admin/transactions", "/admin/inquiries",
    "/admin/lookups", "/admin/audit", "/admin/audit?action=INSERT",
    "/database",
]

LOGINS = {
    "customer": ("john", "User@123", CUSTOMER_PAGES),
    "agent": ("sarah", "Agent@123", AGENT_PAGES),
    "admin": ("admin", "Admin@123", ADMIN_PAGES),
}


def check(client: TestClient, paths: list[str], label: str,
          expect_setup_page: bool) -> list[tuple[str, str]]:
    """Request each path; return a list of (path, problem)."""
    problems: list[tuple[str, str]] = []
    print(f"\n  {label}")
    for path in paths:
        try:
            response = client.get(path, follow_redirects=True)
        except Exception as exc:  # noqa: BLE001
            problems.append((path, f"raised {type(exc).__name__}: {exc}"))
            print(f"    !!  {path}  raised {type(exc).__name__}")
            continue

        body = response.text
        note = ""
        if response.status_code != 200:
            problems.append((path, f"HTTP {response.status_code}"))
            note = f"  <-- HTTP {response.status_code}"
        elif expect_setup_page and "Could Not Connect to PostgreSQL Database" not in body:
            # Without a database every page must be the setup page.  Anything
            # else means the guard was bypassed and the page rendered anyway.
            problems.append((path, "expected the setup page, got a real page"))
            note = "  <-- not the setup page"
        elif not expect_setup_page and "Could Not Connect to PostgreSQL Database" in body:
            problems.append((path, "database was up but the page shows setup help"))
            note = "  <-- setup page despite a live database"

        print(f"    {response.status_code}  {path}  {len(body):>6} bytes{note}")
    return problems


def main() -> int:
    print("=" * 66)
    print("  EstateDB smoke test")
    print("=" * 66)

    problems: list[tuple[str, str]] = []

    # Entering the context manager runs the lifespan hook, which is what tries
    # to open the pool.  Whether that succeeds decides what we assert below.
    with TestClient(app) as client:
        live = db.STARTUP_ERROR is None
        print(f"  driver mode : {db.CLIENT_MODE}")
        if db.CLIENT_WARNING:
            print(f"  warning     : {db.CLIENT_WARNING}")
        if live:
            print("  database    : CONNECTED -- checking real pages")
        else:
            print("  database    : not reachable -- checking the setup page")
            print(f"                {db.STARTUP_ERROR.splitlines()[0]}")

        problems += check(client, PUBLIC_PAGES, "public pages", not live)

        for role, (username, password, pages) in LOGINS.items():
            if live:
                response = client.post(
                    "/login",
                    data={"username": username, "password": password},
                    follow_redirects=True,
                )
                signed_in = response.status_code == 200 and "Sign in" not in \
                    response.text[:2000]
                if not signed_in:
                    problems.append((f"/login as {username}",
                                     "login did not appear to succeed"))
                    print(f"\n  {role}: login as {username} FAILED")
                    continue
            problems += check(client, pages, f"{role} pages (as {username})",
                              not live)
            if live:
                client.get("/logout", follow_redirects=True)

    print("\n" + "=" * 66)
    if problems:
        print(f"  {len(problems)} problem(s):")
        for path, problem in problems:
            print(f"    {path}: {problem}")
        print("=" * 66)
        return 1

    total = len(PUBLIC_PAGES) + sum(len(p) for _, _, p in LOGINS.values())
    print(f"  {total} page request(s), no errors.")
    if db.STARTUP_ERROR:
        print("  Note: this ran WITHOUT a database, so it proved the routing,")
        print("  middleware and template layers only. Run it again once PostgreSQL")
        print("  is up to test the queries.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
