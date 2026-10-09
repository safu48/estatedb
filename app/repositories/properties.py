"""Property queries: filtered search, detail pages and full CRUD.

SQL techniques on show in this module:
* Dynamic WHERE building with parameterised bind variables (protects against SQL injection).
* MySQL LIMIT / OFFSET pagination.
* Reading from a view (v_property_listings) instead of repeating multi-table joins.
* EXISTS sub-queries for amenity filtering and text keyword search.
* Correlated sub-queries for "similar properties".
* Multi-table atomic transactions on create/update (property + images + amenities committed together).
"""
from typing import Any, Optional

from .. import database as db

# Whitelisted sort options.
SORT_OPTIONS = {
    "newest": "created_at DESC",
    "oldest": "created_at ASC",
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "area_desc": "(area_sqft IS NULL), area_sqft DESC",
    "beds_desc": "bedrooms DESC",
}
DEFAULT_SORT = "newest"


def _build_where(f: dict) -> tuple[str, dict]:
    """Turn a dict of optional filters into a WHERE clause + bind parameters."""
    clauses: list[str] = []
    params: dict[str, Any] = {}

    if f.get("city_id"):
        clauses.append("v.city_id = :city_id")
        params["city_id"] = int(f["city_id"])

    if f.get("type_id"):
        clauses.append("v.type_id = :type_id")
        params["type_id"] = int(f["type_id"])

    if f.get("listing_type"):
        clauses.append("v.listing_type = :listing_type")
        params["listing_type"] = f["listing_type"]

    if f.get("status"):
        clauses.append("v.status = :status")
        params["status"] = f["status"]

    if f.get("agent_id"):
        clauses.append("v.agent_id = :agent_id")
        params["agent_id"] = int(f["agent_id"])

    if f.get("min_price") not in (None, ""):
        clauses.append("v.price >= :min_price")
        params["min_price"] = float(f["min_price"])

    if f.get("max_price") not in (None, ""):
        clauses.append("v.price <= :max_price")
        params["max_price"] = float(f["max_price"])

    if f.get("bedrooms"):
        clauses.append("v.bedrooms >= :bedrooms")
        params["bedrooms"] = int(f["bedrooms"])

    if f.get("bathrooms"):
        clauses.append("v.bathrooms >= :bathrooms")
        params["bathrooms"] = int(f["bathrooms"])

    if f.get("min_area"):
        clauses.append("v.area_sqft >= :min_area")
        params["min_area"] = float(f["min_area"])

    if f.get("featured"):
        clauses.append("v.featured = 'Y'")

    if f.get("keyword"):
        clauses.append(
            "(UPPER(v.title) LIKE :kw"
            " OR UPPER(v.address) LIKE :kw"
            " OR EXISTS (SELECT 1 FROM properties pd"
            "             WHERE pd.property_id = v.property_id"
            "               AND UPPER(pd.description) LIKE :kw))"
        )
        params["kw"] = f"%{f['keyword'].upper()}%"

    if f.get("amenity_id"):
        clauses.append(
            "EXISTS (SELECT 1 FROM property_amenities pa"
            "         WHERE pa.property_id = v.property_id"
            "           AND pa.amenity_id = :amenity_id)"
        )
        params["amenity_id"] = int(f["amenity_id"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def search(filters: dict, page: int = 1, per_page: int = 9,
           sort: str = DEFAULT_SORT) -> list[dict]:
    """Return one page of listings matching filters."""
    where, params = _build_where(filters)
    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS[DEFAULT_SORT])

    page = max(1, int(page))
    params["lim"] = per_page
    params["offset"] = (page - 1) * per_page

    sql = f"""
        SELECT v.*
          FROM v_property_listings v
          {where}
         ORDER BY {order_by}, v.property_id
         LIMIT :lim OFFSET :offset
    """
    return db.query(sql, params)


def count(filters: dict) -> int:
    """Total rows matching filters (drives the pager)."""
    where, params = _build_where(filters)
    sql = f"SELECT COUNT(*) FROM v_property_listings v {where}"
    return int(db.scalar(sql, params) or 0)


def get(property_id: int) -> Optional[dict]:
    """One listing from the view, plus description and months listed."""
    row = db.query_one(
        "SELECT * FROM v_property_listings WHERE property_id = :id",
        {"id": property_id},
    )
    if not row:
        return None

    extra = db.query_one(
        "SELECT description FROM properties WHERE property_id = :id",
        {"id": property_id},
    )
    row["description"] = (extra or {}).get("description")
    row["months_listed"] = db.call_months_listed(property_id)
    return row


def images(property_id: int) -> list[dict]:
    """Gallery for one property, cover photo first."""
    return db.query(
        """
        SELECT image_id, image_url, is_primary
          FROM property_images
         WHERE property_id = :id
         ORDER BY (is_primary = 'Y') DESC, image_id
        """,
        {"id": property_id},
    )


def amenities(property_id: int) -> list[dict]:
    """Amenities for one property."""
    return db.query(
        """
        SELECT a.amenity_id, a.amenity_name
          FROM property_amenities pa
          JOIN amenities a ON a.amenity_id = pa.amenity_id
         WHERE pa.property_id = :id
         ORDER BY a.amenity_name
        """,
        {"id": property_id},
    )


def similar(property_id: int, limit: int = 3) -> list[dict]:
    """Other listings in the same city within +/-25% of the price."""
    return db.query(
        """
        SELECT v.*
          FROM v_property_listings v
         WHERE v.property_id <> :id
           AND v.status = 'AVAILABLE'
           AND v.city_id = (SELECT p.city_id FROM properties p
                             WHERE p.property_id = :id)
           AND v.price BETWEEN (SELECT p.price * 0.75 FROM properties p
                                 WHERE p.property_id = :id)
                           AND (SELECT p.price * 1.25 FROM properties p
                                 WHERE p.property_id = :id)
         ORDER BY ABS(v.price - (SELECT p.price FROM properties p
                                  WHERE p.property_id = :id))
         LIMIT :lim
        """,
        {"id": property_id, "lim": limit},
    )


def featured(limit: int = 6) -> list[dict]:
    """Featured available listings for the home page."""
    return db.query(
        """
        SELECT v.* FROM v_property_listings v
         WHERE v.featured = 'Y' AND v.status = 'AVAILABLE'
         ORDER BY v.created_at DESC
         LIMIT :lim
        """,
        {"lim": limit},
    )


def newest(limit: int = 6) -> list[dict]:
    """Most recently listed available properties."""
    return db.query(
        """
        SELECT v.* FROM v_property_listings v
         WHERE v.status = 'AVAILABLE'
         ORDER BY v.created_at DESC
         LIMIT :lim
        """,
        {"lim": limit},
    )


def by_agent(agent_id: int) -> list[dict]:
    """Every listing belonging to one agent."""
    return db.query(
        """
        SELECT * FROM v_property_listings
         WHERE agent_id = :aid
         ORDER BY created_at DESC
        """,
        {"aid": agent_id},
    )


def create(data: dict, image_urls: list[str], amenity_ids: list[int]) -> int:
    """Insert a property together with its images and amenities."""
    with db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO properties
                       (title, description, type_id, city_id, agent_id, address,
                        price, bedrooms, bathrooms, area_sqft, year_built,
                        listing_type, status, featured)
                VALUES (%(title)s, %(description)s, %(type_id)s, %(city_id)s, %(agent_id)s,
                        %(address)s, %(price)s, %(bedrooms)s, %(bathrooms)s, %(area_sqft)s,
                        %(year_built)s, %(listing_type)s, %(status)s, %(featured)s)
                RETURNING property_id
                """,
                data,
            )
            row = cur.fetchone()
            property_id = row["property_id"] if isinstance(row, dict) else row[0]

            for idx, url in enumerate(u for u in image_urls if u.strip()):
                cur.execute(
                    """
                    INSERT INTO property_images (property_id, image_url, is_primary)
                    VALUES (%(pid)s, %(url)s, %(prim)s)
                    """,
                    {"pid": property_id, "url": url.strip(),
                     "prim": "Y" if idx == 0 else "N"},
                )

            if amenity_ids:
                cur.executemany(
                    "INSERT INTO property_amenities (property_id, amenity_id)"
                    " VALUES (%(pid)s, %(aid)s)",
                    [{"pid": property_id, "aid": int(a)} for a in amenity_ids],
                )

            return property_id


def update(property_id: int, data: dict,
           amenity_ids: Optional[list[int]] = None) -> None:
    """Update a property and, if given, replace its amenity set."""
    with db.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE properties
                   SET title        = %(title)s,
                       description  = %(description)s,
                       type_id      = %(type_id)s,
                       city_id      = %(city_id)s,
                       address      = %(address)s,
                       price        = %(price)s,
                       bedrooms     = %(bedrooms)s,
                       bathrooms    = %(bathrooms)s,
                       area_sqft    = %(area_sqft)s,
                       year_built   = %(year_built)s,
                       listing_type = %(listing_type)s,
                       status       = %(status)s,
                       featured     = %(featured)s
                 WHERE property_id  = %(property_id)s
                """,
                {**data, "property_id": property_id},
            )

            if amenity_ids is not None:
                cur.execute(
                    "DELETE FROM property_amenities WHERE property_id = %(pid)s",
                    {"pid": property_id},
                )
                if amenity_ids:
                    cur.executemany(
                        "INSERT INTO property_amenities (property_id, amenity_id)"
                        " VALUES (%(pid)s, %(aid)s)",
                        [{"pid": property_id, "aid": int(a)} for a in amenity_ids],
                    )


def add_image(property_id: int, url: str, is_primary: bool = False) -> None:
    """Append one photo. Setting a new cover clears the previous one first."""
    with db.transaction() as conn:
        with conn.cursor() as cur:
            if is_primary:
                cur.execute(
                    "UPDATE property_images SET is_primary = 'N'"
                    " WHERE property_id = %(pid)s",
                    {"pid": property_id},
                )
            cur.execute(
                "INSERT INTO property_images (property_id, image_url, is_primary)"
                " VALUES (%(pid)s, %(url)s, %(prim)s)",
                {"pid": property_id, "url": url, "prim": "Y" if is_primary else "N"},
            )


def delete_image(image_id: int) -> int:
    return db.execute(
        "DELETE FROM property_images WHERE image_id = :id", {"id": image_id}
    )


def set_status(property_id: int, status: str) -> int:
    """Change availability. Fires trg_properties_after_update trigger."""
    return db.execute(
        "UPDATE properties SET status = :st WHERE property_id = :id",
        {"st": status, "id": property_id},
    )


def toggle_featured(property_id: int) -> int:
    """Flip the featured flag."""
    return db.execute(
        """
        UPDATE properties
           SET featured = CASE featured WHEN 'Y' THEN 'N' ELSE 'Y' END
         WHERE property_id = :id
        """,
        {"id": property_id},
    )


def delete(property_id: int) -> int:
    """Delete a listing."""
    return db.execute(
        "DELETE FROM properties WHERE property_id = :id", {"id": property_id}
    )


def owner_agent_id(property_id: int) -> Optional[int]:
    """Which agent owns this listing."""
    value = db.scalar(
        "SELECT agent_id FROM properties WHERE property_id = :id",
        {"id": property_id},
    )
    return int(value) if value is not None else None
