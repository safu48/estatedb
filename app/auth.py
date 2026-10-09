"""Authentication helpers: password hashing and session-based access control.

Passwords are stored as PBKDF2-HMAC-SHA256 (100k iterations) with a per-user
random salt -- both the hash and the salt live in the USERS table.  The exact
same scheme is used by ``scripts/gen_password.py`` to seed the demo accounts,
so the hashes in ``06_seed.sql`` verify against the passwords documented in the
README.
"""
import hashlib
import hmac
import os
from typing import Optional

from starlette.requests import Request

# --- password scheme constants (must match the seed data generator) ---------
_ITERATIONS = 100_000
_ALGO = "sha256"
_DK_LEN = 32  # derived-key length in bytes

# Role names as stored in the ROLES table.
ROLE_ADMIN = "Admin"
ROLE_AGENT = "Agent"
ROLE_CUSTOMER = "Customer"


def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    """Return ``(hash_hex, salt_hex)`` for the given password.

    A new random salt is generated unless one is supplied (supplying one is
    only used when re-hashing to verify an existing password).
    """
    if salt_hex is None:
        salt_hex = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac(
        _ALGO, password.encode("utf-8"), bytes.fromhex(salt_hex), _ITERATIONS, _DK_LEN
    )
    return dk.hex(), salt_hex


def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    """Constant-time check of a password against the stored hash."""
    candidate, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, stored_hash)


# ---------------------------------------------------------------------------
#  Session helpers.  The logged-in user dict is kept in the signed session
#  cookie (Starlette SessionMiddleware) as:
#     {"user_id", "username", "full_name", "role", "agent_id"}
# ---------------------------------------------------------------------------
class AuthRedirect(Exception):
    """Raised to bounce an unauthenticated/forbidden request to another URL."""

    def __init__(self, location: str):
        self.location = location
        super().__init__(location)


def current_user(request: Request) -> Optional[dict]:
    """Return the logged-in user dict, or None.

    ``request.session`` only exists once SessionMiddleware has run.  The
    database-guard middleware in ``main.py`` sits *outside* it, so when the
    database is down and that guard renders a page directly, the session is not
    there yet -- hence the scope check rather than a bare ``request.session``.
    """
    if "session" not in request.scope:
        return None
    return request.session.get("user")


def login_user(request: Request, user: dict) -> None:
    request.session["user"] = user


def logout_user(request: Request) -> None:
    request.session.pop("user", None)


def require_login(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise AuthRedirect("/login?next=" + request.url.path)
    return user


def require_role(request: Request, *roles: str) -> dict:
    """Ensure the current user is logged in and holds one of ``roles``."""
    user = require_login(request)
    if user["role"] not in roles:
        raise AuthRedirect("/?error=forbidden")
    return user
