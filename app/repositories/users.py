"""User accounts: login lookups, registration and admin management.

Techniques: join to ROLES to resolve the role name, LAST_INSERT_ID() to
capture an AUTO_INCREMENT key, a two-table atomic transaction when creating an
agent (USERS + AGENTS share a primary key), and aggregate reporting grouped
by role.
"""
from typing import Optional

from .. import auth, database as db


def get_by_username(username: str) -> Optional[dict]:
    """Fetch a user (with role name and agent flag) for the login form.

    Accepts either the username or the e-mail address in the same field.
    """
    return db.query_one(
        """
        SELECT u.user_id, u.username, u.email, u.password_hash, u.password_salt,
               u.full_name, u.phone, u.is_active, u.created_at,
               r.role_name,
               (SELECT a.agent_id FROM agents a
                 WHERE a.agent_id = u.user_id) AS agent_id
          FROM users u
          JOIN roles r ON r.role_id = u.role_id
         WHERE UPPER(u.username) = UPPER(:uname)
            OR UPPER(u.email)    = UPPER(:uname)
        """,
        {"uname": username},
    )


def get_by_id(user_id: int) -> Optional[dict]:
    return db.query_one(
        """
        SELECT u.user_id, u.username, u.email, u.full_name, u.phone,
               u.is_active, u.created_at, r.role_name
          FROM users u
          JOIN roles r ON r.role_id = u.role_id
         WHERE u.user_id = :id
        """,
        {"id": user_id},
    )


def username_taken(username: str, email: str) -> bool:
    """One round trip that checks both UNIQUE columns before we insert."""
    count = db.scalar(
        """
        SELECT COUNT(*) FROM users
        WHERE UPPER(username) = UPPER(:uname)
           OR UPPER(email)    = UPPER(:email)
        """,
        {"uname": username, "email": email},
    )
    return bool(count)


def role_id(role_name: str) -> Optional[int]:
    value = db.scalar(
        "SELECT role_id FROM roles WHERE role_name = :rn", {"rn": role_name}
    )
    return int(value) if value is not None else None


def create_customer(username: str, email: str, password: str,
                    full_name: str, phone: str) -> int:
    """Register a self-service customer account."""
    pwd_hash, salt = auth.hash_password(password)
    return db.insert_returning_id(
        """
        INSERT INTO users (username, email, password_hash, password_salt,
                           full_name, phone, role_id)
        VALUES (:username, :email, :pwd_hash, :salt, :full_name, :phone,
                (SELECT role_id FROM roles WHERE role_name = 'Customer'))
        """,
        {"username": username, "email": email, "pwd_hash": pwd_hash,
         "salt": salt, "full_name": full_name, "phone": phone},
    )


def create_agent(username: str, email: str, password: str, full_name: str,
                 phone: str, license_no: str, agency_name: str,
                 commission_rate: float, bio: str = "") -> int:
    """Create an agent: one row in USERS and one in AGENTS, atomically.

    AGENTS.agent_id is a foreign key to USERS.user_id, so the two inserts must
    succeed or fail together -- exactly what db.transaction() gives us.
    """
    pwd_hash, salt = auth.hash_password(password)
    with db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, password_salt,
                                   full_name, phone, role_id)
                VALUES (%(username)s, %(email)s, %(pwd_hash)s, %(salt)s, %(full_name)s, %(phone)s,
                        (SELECT role_id FROM roles WHERE role_name = 'Agent'))
                RETURNING user_id
                """,
                {"username": username, "email": email, "pwd_hash": pwd_hash,
                 "salt": salt, "full_name": full_name, "phone": phone},
            )
            row = cur.fetchone()
            user_id = row["user_id"] if isinstance(row, dict) else row[0]

            cur.execute(
                """
                INSERT INTO agents (agent_id, license_no, agency_name, bio,
                                    commission_rate)
                VALUES (%(agent_id)s, %(license_no)s, %(agency_name)s, %(bio)s, %(rate)s)
                """,
                {"agent_id": user_id, "license_no": license_no,
                 "agency_name": agency_name, "bio": bio,
                 "rate": commission_rate},
            )
            return user_id


def list_all(role_name: Optional[str] = None) -> list[dict]:
    """All users, optionally filtered by role, newest first."""
    return db.query(
        """
        SELECT u.user_id, u.username, u.email, u.full_name, u.phone,
               u.is_active, u.created_at, r.role_name,
               (SELECT COUNT(*) FROM favorites f WHERE f.user_id = u.user_id)
                   AS favorite_count,
               (SELECT COUNT(*) FROM inquiries i WHERE i.customer_id = u.user_id)
                   AS inquiry_count
          FROM users u
          JOIN roles r ON r.role_id = u.role_id
         WHERE :role_name IS NULL OR r.role_name = :role_name
         ORDER BY u.created_at DESC, u.user_id DESC
        """,
        {"role_name": role_name},
    )


def toggle_active(user_id: int) -> int:
    """Enable / disable an account (CASE inside UPDATE)."""
    return db.execute(
        """
        UPDATE users
           SET is_active = CASE is_active WHEN 'Y' THEN 'N' ELSE 'Y' END
         WHERE user_id = :id
        """,
        {"id": user_id},
    )


def update_profile(user_id: int, full_name: str, phone: str, email: str) -> int:
    return db.execute(
        """
        UPDATE users
           SET full_name = :full_name, phone = :phone, email = :email
         WHERE user_id = :id
        """,
        {"id": user_id, "full_name": full_name, "phone": phone, "email": email},
    )


def change_password(user_id: int, new_password: str) -> int:
    pwd_hash, salt = auth.hash_password(new_password)
    return db.execute(
        """
        UPDATE users SET password_hash = :pwd_hash, password_salt = :salt
         WHERE user_id = :id
        """,
        {"id": user_id, "pwd_hash": pwd_hash, "salt": salt},
    )


def counts_by_role() -> list[dict]:
    """User totals per role, including roles nobody holds yet."""
    return db.query(
        """
        SELECT r.role_name,
               COUNT(u.user_id)                                        AS user_count,
               SUM(CASE WHEN u.is_active = 'Y' THEN 1 ELSE 0 END)      AS active_count
          FROM roles r
          LEFT JOIN users u ON u.role_id = r.role_id
         GROUP BY r.role_name
         ORDER BY user_count DESC
        """
    )
