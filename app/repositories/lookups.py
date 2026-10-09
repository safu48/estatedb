"""Reference-data queries (cities, property types, amenities).

Techniques: simple ordered SELECTs for filter drop-downs, aggregate
counts for admin screens, NOT IN sub-query to find unused rows,
and guarded DELETEs that respect foreign keys.
"""
from typing import Optional

from .. import database as db


# ---------------------------------------------------------------------------
#  Read
# ---------------------------------------------------------------------------
def cities() -> list[dict]:
    return db.query(
        "SELECT city_id, city_name, state, country FROM cities"
        " ORDER BY city_name"
    )


def property_types() -> list[dict]:
    return db.query(
        "SELECT type_id, type_name FROM property_types ORDER BY type_name"
    )


def amenities() -> list[dict]:
    return db.query(
        "SELECT amenity_id, amenity_name FROM amenities ORDER BY amenity_name"
    )


def cities_with_counts() -> list[dict]:
    """Cities plus how many listings each has -- straight from the view."""
    return db.query(
        """
        SELECT city_id, city_name, state, property_count, avg_price,
               min_price, max_price, available_count
          FROM v_city_stats
         ORDER BY property_count DESC, city_name
        """
    )


def types_with_counts() -> list[dict]:
    """Property types with listing counts (LEFT JOIN keeps unused types)."""
    return db.query(
        """
        SELECT pt.type_id,
               pt.type_name,
               COUNT(p.property_id)               AS property_count,
               COALESCE(ROUND(AVG(p.price), 0), 0) AS avg_price
          FROM property_types pt
          LEFT JOIN properties p ON p.type_id = pt.type_id
         GROUP BY pt.type_id, pt.type_name
         ORDER BY property_count DESC, pt.type_name
        """
    )


def amenities_with_counts() -> list[dict]:
    """How often each amenity is used, most popular first."""
    return db.query(
        """
        SELECT a.amenity_id,
               a.amenity_name,
               COUNT(pa.property_id) AS usage_count
          FROM amenities a
          LEFT JOIN property_amenities pa ON pa.amenity_id = a.amenity_id
         GROUP BY a.amenity_id, a.amenity_name
         ORDER BY usage_count DESC, a.amenity_name
        """
    )


def unused_amenities() -> list[dict]:
    """Amenities attached to no property at all (NOT IN)."""
    return db.query(
        """
        SELECT amenity_id, amenity_name FROM amenities
         WHERE amenity_id NOT IN (SELECT DISTINCT amenity_id FROM property_amenities)
         ORDER BY amenity_name
        """
    )


# ---------------------------------------------------------------------------
#  Write (admin screens)
# ---------------------------------------------------------------------------
def add_city(city_name: str, state: str, country: str = "USA") -> int:
    return db.insert_returning_id(
        """
        INSERT INTO cities (city_name, state, country)
        VALUES (:city_name, :state, :country)
        """,
        {"city_name": city_name, "state": state, "country": country},
    )


def add_property_type(type_name: str) -> int:
    return db.insert_returning_id(
        "INSERT INTO property_types (type_name) VALUES (:type_name)",
        {"type_name": type_name},
    )


def add_amenity(amenity_name: str) -> int:
    return db.insert_returning_id(
        "INSERT INTO amenities (amenity_name) VALUES (:amenity_name)",
        {"amenity_name": amenity_name},
    )


def rename_city(city_id: int, city_name: str, state: str) -> int:
    return db.execute(
        "UPDATE cities SET city_name = :city_name, state = :state"
        " WHERE city_id = :city_id",
        {"city_id": city_id, "city_name": city_name, "state": state},
    )


def delete_amenity(amenity_id: int) -> int:
    """Remove an amenity and every property link to it (one transaction)."""
    with db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM property_amenities WHERE amenity_id = %(id)s",
                {"id": amenity_id},
            )
            cur.execute(
                "DELETE FROM amenities WHERE amenity_id = %(id)s", {"id": amenity_id}
            )
            return cur.rowcount


def delete_city(city_id: int) -> int:
    """Delete a city (blocked by foreign key if referenced by properties)."""
    return db.execute("DELETE FROM cities WHERE city_id = :id", {"id": city_id})


def price_range() -> dict:
    """Global min/max price, used to set sensible slider bounds on the filters."""
    row = db.query_one(
        """
        SELECT COALESCE(MIN(price), 0)             AS min_price,
               COALESCE(MAX(price), 0)             AS max_price,
               COALESCE(ROUND(AVG(price), 0), 0)   AS avg_price
          FROM properties
        """
    )
    return row or {"min_price": 0, "max_price": 0, "avg_price": 0}
