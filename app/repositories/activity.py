"""Customer activity: viewing inquiries and saved (favourite) properties.

Techniques: joins across three tables for inbox views, a stored procedure
call to update inquiry workflows, aggregate counts with GROUP BY, an
INSERT IGNORE / DELETE pair for the favourites toggle, and NOT EXISTS
for listing recommendations.
"""
from typing import Optional

from .. import database as db


# ---------------------------------------------------------------------------
#  Inquiries
# ---------------------------------------------------------------------------
def create_inquiry(property_id: int, customer_id: int, message: str,
                   preferred_date: Optional[str]) -> int:
    """Log a viewing request."""
    return db.insert_returning_id(
        """
        INSERT INTO inquiries (property_id, customer_id, message, preferred_date)
        VALUES (:pid, :cid, :msg, :pref_date)
        """,
        {"pid": property_id, "cid": customer_id, "msg": message,
         "pref_date": preferred_date or None},
    )


def inquiries_by_customer(customer_id: int) -> list[dict]:
    """A customer's own inquiries, with the property and agent they concern."""
    return db.query(
        """
        SELECT i.inquiry_id, i.message, i.preferred_date, i.status, i.created_at,
               p.property_id, p.title, p.price, p.listing_type, p.status AS property_status,
               c.city_name,
               a.agent_id,
               u.full_name AS agent_name, u.phone AS agent_phone
          FROM inquiries i
          JOIN properties p ON p.property_id = i.property_id
          JOIN cities     c ON c.city_id     = p.city_id
          JOIN agents     a ON a.agent_id    = p.agent_id
          JOIN users      u ON u.user_id     = a.agent_id
         WHERE i.customer_id = :cid
         ORDER BY i.created_at DESC
        """,
        {"cid": customer_id},
    )


def inquiries_for_agent(agent_id: int, status: Optional[str] = None) -> list[dict]:
    """The agent's inbox: inquiries on any property they listed."""
    return db.query(
        """
        SELECT i.inquiry_id, i.message, i.preferred_date, i.status, i.created_at,
               p.property_id, p.title, p.price,
               u.user_id AS customer_id, u.full_name AS customer_name,
               u.email AS customer_email, u.phone AS customer_phone
          FROM inquiries i
          JOIN properties p ON p.property_id = i.property_id
          JOIN users      u ON u.user_id     = i.customer_id
         WHERE p.agent_id = :aid
           AND (:status IS NULL OR i.status = :status)
         ORDER BY CASE i.status
                     WHEN 'NEW' THEN 0
                     WHEN 'CONTACTED' THEN 1
                     WHEN 'SCHEDULED' THEN 2
                     ELSE 3
                  END,
                  i.created_at DESC
        """,
        {"aid": agent_id, "status": status},
    )


def all_inquiries() -> list[dict]:
    """Every inquiry in the system (admin view)."""
    return db.query(
        """
        SELECT i.inquiry_id, i.status, i.created_at, i.preferred_date, i.message,
               p.title AS property_title,
               cu.full_name AS customer_name,
               ag.full_name AS agent_name
          FROM inquiries i
          JOIN properties p  ON p.property_id = i.property_id
          JOIN users      cu ON cu.user_id    = i.customer_id
          JOIN agents     a  ON a.agent_id    = p.agent_id
          JOIN users      ag ON ag.user_id    = a.agent_id
         ORDER BY i.created_at DESC
        """
    )


def set_inquiry_status(inquiry_id: int, status: str) -> None:
    """Delegate to the sp_update_inquiry_status stored procedure."""
    db.call_update_inquiry_status(inquiry_id, status)


def inquiry_owner_agent(inquiry_id: int) -> Optional[int]:
    """Which agent an inquiry belongs to (authorisation check)."""
    value = db.scalar(
        """
        SELECT p.agent_id
          FROM inquiries i
          JOIN properties p ON p.property_id = i.property_id
         WHERE i.inquiry_id = :iid
        """,
        {"iid": inquiry_id},
    )
    return int(value) if value is not None else None


def inquiry_counts_by_status(agent_id: Optional[int] = None) -> list[dict]:
    """NEW / CONTACTED / SCHEDULED / CLOSED totals, optionally for one agent."""
    return db.query(
        """
        SELECT i.status, COUNT(*) AS status_count
          FROM inquiries i
          JOIN properties p ON p.property_id = i.property_id
         WHERE :aid IS NULL OR p.agent_id = :aid
         GROUP BY i.status
         ORDER BY CASE i.status
                     WHEN 'NEW' THEN 0
                     WHEN 'CONTACTED' THEN 1
                     WHEN 'SCHEDULED' THEN 2
                     ELSE 3
                  END
        """,
        {"aid": agent_id},
    )


# ---------------------------------------------------------------------------
#  Favourites
# ---------------------------------------------------------------------------
def is_favorite(user_id: int, property_id: int) -> bool:
    count = db.scalar(
        "SELECT COUNT(*) FROM favorites WHERE user_id = :user_id AND property_id = :pid",
        {"user_id": user_id, "pid": property_id},
    )
    return bool(count)


def add_favorite(user_id: int, property_id: int) -> None:
    """Save a property safely (ON CONFLICT DO NOTHING prevents duplicate errors)."""
    db.execute(
        "INSERT INTO favorites (user_id, property_id) VALUES (:user_id, :pid) ON CONFLICT DO NOTHING",
        {"user_id": user_id, "pid": property_id},
    )


def remove_favorite(user_id: int, property_id: int) -> int:
    return db.execute(
        "DELETE FROM favorites WHERE user_id = :user_id AND property_id = :pid",
        {"user_id": user_id, "pid": property_id},
    )


def toggle_favorite(user_id: int, property_id: int) -> bool:
    """Add or remove in one call. Returns True if the property is now saved."""
    if is_favorite(user_id, property_id):
        remove_favorite(user_id, property_id)
        return False
    add_favorite(user_id, property_id)
    return True


def favorites_for(user_id: int) -> list[dict]:
    """A customer's saved listings, most recently saved first."""
    return db.query(
        """
        SELECT v.*, f.added_at
          FROM favorites f
          JOIN v_property_listings v ON v.property_id = f.property_id
         WHERE f.user_id = :user_id
         ORDER BY f.added_at DESC
        """,
        {"user_id": user_id},
    )


def favorite_ids(user_id: int) -> set:
    """Set of saved property ids, so listing cards can show a filled heart."""
    rows = db.query(
        "SELECT property_id FROM favorites WHERE user_id = :user_id", {"user_id": user_id}
    )
    return {int(r["property_id"]) for r in rows}


def recommendations(user_id: int, limit: int = 3) -> list[dict]:
    """Suggest listings in the cities the customer has already shown interest in."""
    return db.query(
        """
        SELECT v.*
          FROM v_property_listings v
         WHERE v.status = 'AVAILABLE'
           AND v.city_id IN (SELECT p.city_id
                               FROM favorites f
                               JOIN properties p ON p.property_id = f.property_id
                              WHERE f.user_id = :user_id)
           AND NOT EXISTS (SELECT 1 FROM favorites f2
                            WHERE f2.user_id = :user_id
                              AND f2.property_id = v.property_id)
         ORDER BY v.featured DESC, v.created_at DESC
         LIMIT :lim
        """,
        {"user_id": user_id, "lim": limit},
    )


def most_favorited(limit: int = 5) -> list[dict]:
    """Listings ranked by how many customers saved them."""
    return db.query(
        """
        SELECT p.property_id, p.title, p.price, p.listing_type,
               c.city_name, COUNT(f.user_id) AS save_count
          FROM properties p
          JOIN cities    c ON c.city_id = p.city_id
          LEFT JOIN favorites f ON f.property_id = p.property_id
         GROUP BY p.property_id, p.title, p.price, p.listing_type, c.city_name
        HAVING COUNT(f.user_id) > 0
         ORDER BY COUNT(f.user_id) DESC, p.title
         LIMIT :lim
        """,
        {"lim": limit},
    )
