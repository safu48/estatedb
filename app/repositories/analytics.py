"""Reporting and analytics for the admin dashboard, plus transaction handling.

Features MySQL analytical SQL techniques:
* Stored function calls in SELECT lists (fn_property_count).
* Window functions: LAG for month-on-month revenue changes, and SUM() OVER (...)
  for running revenue totals.
* ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...) to pick priciest listing per city.
* GROUP BY ... WITH ROLLUP and GROUPING() for subtotal and grand-total aggregations.
* Conditional aggregation for crosstabs.
* UNION ALL to merge multi-table activity streams.
* Stored procedure call (sp_record_sale) to execute transactions with database validation.
"""
from typing import Optional

from .. import database as db


# ---------------------------------------------------------------------------
#  Headline numbers
# ---------------------------------------------------------------------------
def kpis() -> dict:
    """Top-of-dashboard totals using stored functions and subqueries."""
    row = db.query_one(
        """
        SELECT fn_property_count(NULL)        AS total_properties,
               fn_property_count('AVAILABLE') AS available_properties,
               fn_property_count('SOLD')      AS sold_properties,
               fn_property_count('RENTED')    AS rented_properties,
               fn_property_count('PENDING')   AS pending_properties,
               (SELECT COUNT(*) FROM users)           AS total_users,
               (SELECT COUNT(*) FROM agents)          AS total_agents,
               (SELECT COUNT(*) FROM inquiries)       AS total_inquiries,
               (SELECT COUNT(*) FROM inquiries WHERE status = 'NEW')
                                                      AS new_inquiries,
               (SELECT COUNT(*) FROM transactions)    AS total_transactions,
               (SELECT COALESCE(SUM(sale_price), 0) FROM transactions)
                                                      AS total_revenue,
               (SELECT COALESCE(SUM(commission_amount), 0) FROM transactions)
                                                      AS total_commission,
               (SELECT COALESCE(ROUND(AVG(price), 0), 0) FROM properties)
                                                      AS avg_price,
               (SELECT COALESCE(ROUND(AVG(NOW()::date - created_at::date), 0), 0)
                  FROM properties WHERE status = 'AVAILABLE')
                                                      AS avg_days_on_market
        """
    )
    return row or {}


# ---------------------------------------------------------------------------
#  Time series
# ---------------------------------------------------------------------------
def monthly_sales() -> list[dict]:
    """Revenue per month with previous month, delta and running total."""
    return db.query(
        """
        SELECT sales_month,
               deal_count,
               revenue,
               commission,
               avg_deal,
               LAG(revenue) OVER (ORDER BY sales_month)              AS prev_revenue,
               revenue - LAG(revenue) OVER (ORDER BY sales_month)    AS revenue_change,
               ROUND( (revenue - LAG(revenue) OVER (ORDER BY sales_month))
                      / NULLIF(LAG(revenue) OVER (ORDER BY sales_month), 0)
                      * 100, 1)                                      AS revenue_change_pct,
               SUM(revenue) OVER (ORDER BY sales_month
                                  ROWS UNBOUNDED PRECEDING)          AS running_revenue
          FROM v_monthly_sales
         ORDER BY sales_month
        """
    )


def listings_added_by_month(months: int = 12) -> list[dict]:
    """How many listings were created each month over the last N months."""
    return db.query(
        """
        SELECT TO_CHAR(created_at, 'YYYY-MM') AS listing_month,
               COUNT(*)                         AS listing_count,
               ROUND(AVG(price), 0)             AS avg_price
          FROM properties
         WHERE created_at >= NOW() - (:months || ' month')::interval
         GROUP BY TO_CHAR(created_at, 'YYYY-MM')
         ORDER BY listing_month
        """,
        {"months": str(months)},
    )


# ---------------------------------------------------------------------------
#  Distributions and crosstabs
# ---------------------------------------------------------------------------
def price_bands() -> list[dict]:
    """Group listings into price bands with a CASE expression."""
    return db.query(
        """
        SELECT CASE
                   WHEN price <  250000 THEN 'Under 250K'
                   WHEN price <  500000 THEN '250K - 500K'
                   WHEN price <  750000 THEN '500K - 750K'
                   WHEN price < 1000000 THEN '750K - 1M'
                   WHEN price < 1500000 THEN '1M - 1.5M'
                   ELSE                      'Over 1.5M'
               END                    AS price_band,
               COUNT(*)               AS property_count,
               ROUND(AVG(area_sqft))  AS avg_area,
               MIN(price)             AS band_min,
               MAX(price)             AS band_max
          FROM properties
         WHERE listing_type = 'SALE'
         GROUP BY CASE
                   WHEN price <  250000 THEN 'Under 250K'
                   WHEN price <  500000 THEN '250K - 500K'
                   WHEN price <  750000 THEN '500K - 750K'
                   WHEN price < 1000000 THEN '750K - 1M'
                   WHEN price < 1500000 THEN '1M - 1.5M'
                   ELSE                      'Over 1.5M'
               END
         ORDER BY MIN(price)
        """
    )


def status_by_type() -> list[dict]:
    """Crosstab of property type against status using conditional aggregation."""
    return db.query(
        """
        SELECT pt.type_name,
               SUM(CASE WHEN p.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN p.status = 'PENDING'   THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN p.status = 'SOLD'      THEN 1 ELSE 0 END) AS sold,
               SUM(CASE WHEN p.status = 'RENTED'    THEN 1 ELSE 0 END) AS rented,
               COUNT(p.property_id)                                    AS total
          FROM property_types pt
          LEFT JOIN properties p ON p.type_id = pt.type_id
         GROUP BY pt.type_name
         ORDER BY total DESC, pt.type_name
        """
    )


def revenue_by_city_rollup() -> list[dict]:
    """Deal revenue per city and type, with subtotals and a grand total (ROLLUP)."""
    return db.query(
        """
        SELECT CASE WHEN c.city_name IS NULL THEN 'ALL CITIES' ELSE c.city_name END AS city_name,
               CASE WHEN t.txn_type IS NULL THEN 'ALL TYPES' ELSE t.txn_type END   AS txn_type,
               COUNT(*)                        AS deal_count,
               SUM(t.sale_price)               AS revenue,
               SUM(t.commission_amount)        AS commission,
               CASE WHEN c.city_name IS NULL THEN 1 ELSE 0 END AS is_city_total,
               CASE WHEN t.txn_type IS NULL THEN 1 ELSE 0 END  AS is_type_total
          FROM transactions t
          JOIN properties p ON p.property_id = t.property_id
          JOIN cities     c ON c.city_id     = p.city_id
         GROUP BY ROLLUP (c.city_name, t.txn_type)
        """
    )


def priciest_per_city() -> list[dict]:
    """The single most expensive available listing in each city (ROW_NUMBER window)."""
    return db.query(
        """
        SELECT city_name, state, property_id, title, price, bedrooms, area_sqft
          FROM (SELECT c.city_name,
                       c.state,
                       p.property_id,
                       p.title,
                       p.price,
                       p.bedrooms,
                       p.area_sqft,
                       ROW_NUMBER() OVER (PARTITION BY c.city_id
                                              ORDER BY p.price DESC) AS rn
                  FROM properties p
                  JOIN cities c ON c.city_id = p.city_id
                 WHERE p.status = 'AVAILABLE') ranked
         WHERE rn = 1
         ORDER BY price DESC
        """
    )


def busy_cities(min_listings: int = 2) -> list[dict]:
    """Cities carrying at least N listings -- a GROUP BY ... HAVING filter."""
    return db.query(
        """
        SELECT c.city_name,
               c.state,
               COUNT(p.property_id)      AS listing_count,
               ROUND(AVG(p.price), 0)    AS avg_price,
               MAX(p.price)              AS top_price
          FROM cities c
          JOIN properties p ON p.city_id = c.city_id
         GROUP BY c.city_name, c.state
        HAVING COUNT(p.property_id) >= :min_listings
         ORDER BY listing_count DESC, avg_price DESC
        """,
        {"min_listings": min_listings},
    )


# ---------------------------------------------------------------------------
#  Activity feed
# ---------------------------------------------------------------------------
def recent_activity(limit: int = 12) -> list[dict]:
    """One combined feed of new inquiries, closed deals and fresh reviews."""
    return db.query(
        """
        SELECT * FROM (
            SELECT 'INQUIRY' AS activity_type,
                   i.created_at AS activity_date,
                   u.full_name  AS actor,
                   p.title      AS subject,
                   CONCAT('Status: ', i.status) AS detail
              FROM inquiries i
              JOIN users u      ON u.user_id = i.customer_id
              JOIN properties p ON p.property_id = i.property_id
            UNION ALL
            SELECT 'DEAL',
                   t.txn_date,
                   u.full_name,
                   p.title,
                   CONCAT(t.txn_type, ' for $', TO_CHAR(t.sale_price, 'FM999,999,999'))
              FROM transactions t
              JOIN users u      ON u.user_id = t.buyer_id
              JOIN properties p ON p.property_id = t.property_id
            UNION ALL
            SELECT 'REVIEW',
                   r.review_date,
                   cu.full_name,
                   ag.full_name,
                   CONCAT(r.rating, ' star rating')
              FROM reviews r
              JOIN users cu ON cu.user_id = r.customer_id
              JOIN agents a ON a.agent_id = r.agent_id
              JOIN users ag ON ag.user_id = a.agent_id
            ORDER BY activity_date DESC
        ) feed
        LIMIT :lim
        """,
        {"lim": limit},
    )


# ---------------------------------------------------------------------------
#  Transactions
# ---------------------------------------------------------------------------
def all_transactions() -> list[dict]:
    """Full deal ledger with property, buyer and agent names."""
    return db.query(
        """
        SELECT t.transaction_id, t.sale_price, t.commission_amount, t.txn_type,
               t.txn_date,
               p.property_id, p.title AS property_title, p.price AS list_price,
               c.city_name,
               b.full_name AS buyer_name,
               ag.full_name AS agent_name,
               ROUND(t.sale_price - p.price, 2) AS price_difference
          FROM transactions t
          JOIN properties p ON p.property_id = t.property_id
          JOIN cities     c ON c.city_id     = p.city_id
          JOIN users      b ON b.user_id     = t.buyer_id
          JOIN agents     a ON a.agent_id    = t.agent_id
          JOIN users     ag ON ag.user_id    = a.agent_id
         ORDER BY t.txn_date DESC, t.transaction_id DESC
        """
    )


def transactions_for_agent(agent_id: int) -> list[dict]:
    return db.query(
        """
        SELECT t.transaction_id, t.sale_price, t.commission_amount, t.txn_type,
               t.txn_date, p.title AS property_title, b.full_name AS buyer_name
          FROM transactions t
          JOIN properties p ON p.property_id = t.property_id
          JOIN users      b ON b.user_id     = t.buyer_id
         WHERE t.agent_id = :aid
         ORDER BY t.txn_date DESC
        """,
        {"aid": agent_id},
    )


def record_sale(property_id: int, buyer_id: int, sale_price: float,
                txn_type: str) -> int:
    """Close a deal through sp_record_sale stored procedure."""
    return db.call_record_sale(property_id, buyer_id, sale_price, txn_type)


def buyers_for_dropdown() -> list[dict]:
    """Customers who could be recorded as a buyer."""
    return db.query(
        """
        SELECT u.user_id, u.full_name, u.email
          FROM users u
          JOIN roles r ON r.role_id = u.role_id
         WHERE r.role_name = 'Customer' AND u.is_active = 'Y'
         ORDER BY u.full_name
        """
    )


# ---------------------------------------------------------------------------
#  Audit trail (populated by triggers)
# ---------------------------------------------------------------------------
def audit_log(limit: int = 50, action: Optional[str] = None) -> list[dict]:
    """Recent audit rows, newest first, optionally filtered by action."""
    return db.query(
        """
        SELECT log_id, table_name, action, record_id, changed_by,
               change_details,
               TO_CHAR(changed_at, 'YYYY-MM-DD HH24:MI:SS') AS changed_at
          FROM audit_log
         WHERE :action IS NULL OR action = :action
         ORDER BY changed_at DESC, log_id DESC
         LIMIT :lim
        """,
        {"action": action, "lim": limit},
    )


def audit_counts() -> list[dict]:
    """How many INSERT / UPDATE / DELETE events have been logged."""
    return db.query(
        """
        SELECT action, COUNT(*) AS event_count
          FROM audit_log
         GROUP BY action
         ORDER BY event_count DESC
        """
    )
