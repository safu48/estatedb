"""Agent directory, agent profiles and customer reviews.

Techniques: reading the v_agent_performance view, calling stored functions
(fn_agent_total_sales / fn_agent_avg_rating) straight from a SELECT list,
INSERT ... ON DUPLICATE KEY UPDATE for review upserts, and RANK() / DENSE_RANK()
window functions for the leaderboard.
"""
from typing import Optional

from .. import database as db


def list_all(sort: str = "sales") -> list[dict]:
    """Agent directory. sort is whitelisted, never interpolated raw."""
    order_by = {
        "sales": "total_sales_value DESC",
        "rating": "(avg_rating IS NULL), avg_rating DESC",
        "listings": "total_listings DESC",
        "name": "agent_name ASC",
    }.get(sort, "total_sales_value DESC")

    return db.query(
        f"""
        SELECT agent_id, agent_name, email, phone, agency_name, commission_rate,
               hire_date, total_listings, closed_listings, total_sales_value,
               total_commission, review_count, avg_rating
          FROM v_agent_performance
         ORDER BY {order_by}, agent_name
        """
    )


def get(agent_id: int) -> Optional[dict]:
    """One agent profile with calculated metrics from stored functions."""
    return db.query_one(
        """
        SELECT vp.*,
               a.bio,
               a.license_no,
               fn_agent_total_sales(vp.agent_id) AS pkg_total_sales,
               fn_agent_avg_rating(vp.agent_id)  AS pkg_avg_rating
          FROM v_agent_performance vp
          JOIN agents a ON a.agent_id = vp.agent_id
         WHERE vp.agent_id = :aid
        """,
        {"aid": agent_id},
    )


def leaderboard(limit: int = 5) -> list[dict]:
    """Top agents by revenue, with RANK() and DENSE_RANK() window functions."""
    return db.query(
        """
        SELECT agent_id,
               agent_name,
               agency_name,
               total_listings,
               closed_listings,
               total_sales_value,
               total_commission,
               avg_rating,
               RANK()       OVER (ORDER BY total_sales_value DESC) AS sales_rank,
               DENSE_RANK() OVER (ORDER BY (avg_rating IS NULL), avg_rating DESC) AS rating_rank
          FROM v_agent_performance
         ORDER BY total_sales_value DESC
         LIMIT :lim
        """,
        {"lim": limit},
    )


def update_profile(agent_id: int, agency_name: str, license_no: str,
                   commission_rate: float, bio: str) -> int:
    return db.execute(
        """
        UPDATE agents
           SET agency_name     = :agency_name,
               license_no      = :license_no,
               commission_rate = :rate,
               bio             = :bio
         WHERE agent_id        = :aid
        """,
        {"aid": agent_id, "agency_name": agency_name,
         "license_no": license_no, "rate": commission_rate, "bio": bio},
    )


# ---------------------------------------------------------------------------
#  Reviews
# ---------------------------------------------------------------------------
def reviews_for(agent_id: int) -> list[dict]:
    """All reviews for one agent, newest first, with the reviewer's name."""
    return db.query(
        """
        SELECT r.review_id, r.rating, r.comments, r.review_date,
               u.full_name AS customer_name
          FROM reviews r
          JOIN users u ON u.user_id = r.customer_id
         WHERE r.agent_id = :aid
         ORDER BY r.review_date DESC
        """,
        {"aid": agent_id},
    )


def review_by(agent_id: int, customer_id: int) -> Optional[dict]:
    """The current user's existing review for this agent, if any."""
    return db.query_one(
        """
        SELECT review_id, rating, comments, review_date
          FROM reviews
         WHERE agent_id = :aid AND customer_id = :cid
        """,
        {"aid": agent_id, "cid": customer_id},
    )


def upsert_review(agent_id: int, customer_id: int, rating: int,
                  comments: str) -> None:
    """Leave a review, or overwrite existing (PostgreSQL ON CONFLICT)."""
    db.execute(
        """
        INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
        VALUES (:aid, :cid, :rating, :comments, NOW())
        ON CONFLICT (agent_id, customer_id) DO UPDATE SET
            rating = EXCLUDED.rating,
            comments = EXCLUDED.comments,
            review_date = NOW()
        """,
        {"aid": agent_id, "cid": customer_id, "rating": rating,
         "comments": comments},
    )


def delete_review(review_id: int, customer_id: int) -> int:
    """Delete a review, scoped to its author."""
    return db.execute(
        "DELETE FROM reviews WHERE review_id = :rid AND customer_id = :cid",
        {"rid": review_id, "cid": customer_id},
    )


def reviews_by_customer(customer_id: int) -> list[dict]:
    """Everything one customer has reviewed (their dashboard)."""
    return db.query(
        """
        SELECT r.review_id, r.rating, r.comments, r.review_date,
               r.agent_id, u.full_name AS agent_name, a.agency_name
          FROM reviews r
          JOIN agents a ON a.agent_id = r.agent_id
          JOIN users  u ON u.user_id  = a.agent_id
         WHERE r.customer_id = :cid
         ORDER BY r.review_date DESC
        """,
        {"cid": customer_id},
    )


def rating_distribution(agent_id: int) -> list[dict]:
    """How many 1..5 star ratings an agent has."""
    return db.query(
        """
        SELECT stars.rating,
               (SELECT COUNT(*) FROM reviews r
                 WHERE r.agent_id = :aid AND r.rating = stars.rating) AS review_count
          FROM (
              SELECT 1 AS rating UNION ALL
              SELECT 2 UNION ALL
              SELECT 3 UNION ALL
              SELECT 4 UNION ALL
              SELECT 5
          ) stars
         ORDER BY stars.rating DESC
        """,
        {"aid": agent_id},
    )
