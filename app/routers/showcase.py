"""A single page that runs one representative query per SQL technique and shows
the statement next to its live result.

This exists for the project write-up / demo: instead of hunting through the
code to prove that joins, sub-queries, analytic functions, set operators,
stored routines, triggers and the MySQL information_schema are all being used,
you can point at one page. Every statement here is read-only, and each runs in
its own try/except so one failure cannot take the page down.
"""
from fastapi import APIRouter, Request

from .. import auth, database as db
from ..templating import render

router = APIRouter()

# Each demo: the technique, a one-line explanation, and the SQL to run.
DEMOS: list[dict] = [
    # ---------------------------------------------------------------- joins
    {
        "group": "Joins",
        "title": "INNER JOIN across four tables",
        "note": "Denormalises a listing into one row: property, type, city and "
                "the agent who listed it.",
        "sql": """
SELECT p.property_id, p.title, pt.type_name, c.city_name, u.full_name AS agent
  FROM properties p
  JOIN property_types pt ON pt.type_id  = p.type_id
  JOIN cities         c  ON c.city_id   = p.city_id
  JOIN agents         a  ON a.agent_id  = p.agent_id
  JOIN users          u  ON u.user_id   = a.agent_id
 LIMIT 8
""",
    },
    {
        "group": "Joins",
        "title": "LEFT OUTER JOIN (keeps rows with no match)",
        "note": "Every city appears, including ones with no listings at all -- "
                "an inner join would silently hide those.",
        "sql": """
SELECT c.city_name, c.state, COUNT(p.property_id) AS listings
  FROM cities c
  LEFT JOIN properties p ON p.city_id = c.city_id
 GROUP BY c.city_name, c.state
 ORDER BY listings ASC, c.city_name
""",
    },
    {
        "group": "Joins",
        "title": "Many-to-many via a bridge table",
        "note": "property_amenities resolves the many-to-many relationship between "
                "properties and amenities.",
        "sql": """
SELECT a.amenity_name, COUNT(pa.property_id) AS used_by
  FROM amenities a
  LEFT JOIN property_amenities pa ON pa.amenity_id = a.amenity_id
 GROUP BY a.amenity_name
 ORDER BY used_by DESC, a.amenity_name
""",
    },
    # ------------------------------------------------------------ aggregates
    {
        "group": "Aggregation",
        "title": "GROUP BY with HAVING",
        "note": "HAVING filters after aggregation -- WHERE cannot do this, "
                "because the count does not exist yet when WHERE runs.",
        "sql": """
SELECT c.city_name,
       COUNT(*)               AS listings,
       ROUND(AVG(p.price), 0) AS avg_price,
       MAX(p.price)           AS top_price
  FROM properties p
  JOIN cities c ON c.city_id = p.city_id
 GROUP BY c.city_name
HAVING COUNT(*) >= 2
 ORDER BY listings DESC
""",
    },
    {
        "group": "Aggregation",
        "title": "GROUP BY ROLLUP",
        "note": "ROLLUP adds subtotal and grand-total rows; IS NULL detects "
                "synthetic rows so they can be styled differently.",
        "sql": """
SELECT CASE WHEN t.txn_type IS NULL THEN 'ALL TYPES' ELSE t.txn_type END AS txn_type,
       COUNT(*)                          AS deals,
       SUM(t.sale_price)                 AS revenue,
       (t.txn_type IS NULL)              AS is_total_row
  FROM transactions t
 GROUP BY ROLLUP (t.txn_type)
""",
    },
    {
        "group": "Aggregation",
        "title": "Conditional aggregation (crosstab / pivot)",
        "note": "Transposes rows into columns using conditional SUM over CASE expressions.",
        "sql": """
SELECT pt.type_name,
       SUM(CASE WHEN p.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available,
       SUM(CASE WHEN p.status = 'PENDING'   THEN 1 ELSE 0 END) AS pending,
       SUM(CASE WHEN p.status = 'SOLD'      THEN 1 ELSE 0 END) AS sold,
       SUM(CASE WHEN p.status = 'RENTED'    THEN 1 ELSE 0 END) AS rented
  FROM property_types pt
  LEFT JOIN properties p ON p.type_id = pt.type_id
 GROUP BY pt.type_name
 ORDER BY pt.type_name
""",
    },
    # ------------------------------------------------------------ subqueries
    {
        "group": "Sub-queries",
        "title": "Sub-query in WHERE (compare against an aggregate)",
        "note": "Listings priced above the overall average. The inner query "
                "runs once and returns a single scalar.",
        "sql": """
SELECT title, price
  FROM properties
 WHERE price > (SELECT AVG(price) FROM properties)
 ORDER BY price DESC
""",
    },
    {
        "group": "Sub-queries",
        "title": "Correlated sub-query in the SELECT list",
        "note": "The inner query re-runs for each outer row, referencing it by "
                "p.property_id.",
        "sql": """
SELECT p.title,
       (SELECT COUNT(*) FROM favorites f  WHERE f.property_id = p.property_id) AS saves,
       (SELECT COUNT(*) FROM inquiries i  WHERE i.property_id = p.property_id) AS inquiries
  FROM properties p
 ORDER BY saves DESC
 LIMIT 10
""",
    },
    {
        "group": "Sub-queries",
        "title": "EXISTS and NOT EXISTS",
        "note": "Agents who have closed at least one deal but have never been "
                "reviewed. EXISTS stops at the first match.",
        "sql": """
SELECT u.full_name
  FROM agents a
  JOIN users u ON u.user_id = a.agent_id
 WHERE EXISTS     (SELECT 1 FROM transactions t WHERE t.agent_id = a.agent_id)
   AND NOT EXISTS (SELECT 1 FROM reviews r      WHERE r.agent_id = a.agent_id)
""",
    },
    {
        "group": "Sub-queries",
        "title": "IN with a sub-query and derived table",
        "note": "Nested query filtering property types combined with derived table aggregation.",
        "sql": """
SELECT city_name, listings
  FROM (SELECT c.city_name, COUNT(*) AS listings
          FROM properties p
          JOIN cities c ON c.city_id = p.city_id
         WHERE p.type_id IN (SELECT type_id FROM property_types
                              WHERE type_name IN ('House', 'Villa'))
         GROUP BY c.city_name) city_summary
 ORDER BY listings DESC
""",
    },
    # ------------------------------------------------------- analytic / window
    {
        "group": "Window functions",
        "title": "RANK, DENSE_RANK and ROW_NUMBER",
        "note": "Window functions rank rows without collapsing them. RANK "
                "leaves gaps after a tie, DENSE_RANK does not.",
        "sql": """
SELECT agent_name,
       total_sales_value,
       RANK()       OVER (ORDER BY total_sales_value DESC) AS rank_with_gaps,
       DENSE_RANK() OVER (ORDER BY total_sales_value DESC) AS dense_rank,
       ROW_NUMBER() OVER (ORDER BY total_sales_value DESC) AS row_number
  FROM v_agent_performance
 ORDER BY total_sales_value DESC
""",
    },
    {
        "group": "Window functions",
        "title": "PARTITION BY -- top listing per city",
        "note": "ROW_NUMBER restarts at 1 for each city, so filtering to rn = 1 "
                "picks one winner per group while still returning the title.",
        "sql": """
SELECT city_name, title, price
  FROM (SELECT c.city_name, p.title, p.price,
               ROW_NUMBER() OVER (PARTITION BY c.city_id
                                      ORDER BY p.price DESC) AS rn
          FROM properties p
          JOIN cities c ON c.city_id = p.city_id) ranked
 WHERE rn = 1
 ORDER BY price DESC
""",
    },
    {
        "group": "Window functions",
        "title": "LAG and a running total",
        "note": "LAG reads the previous month's revenue; SUM() OVER (...) "
                "computes a cumulative running total across months.",
        "sql": """
SELECT sales_month,
       revenue,
       LAG(revenue) OVER (ORDER BY sales_month)           AS prev_month,
       revenue - LAG(revenue) OVER (ORDER BY sales_month) AS delta,
       SUM(revenue) OVER (ORDER BY sales_month
                          ROWS UNBOUNDED PRECEDING)       AS running_total
  FROM v_monthly_sales
 ORDER BY sales_month
""",
    },
    # --------------------------------------------------------- set operators
    {
        "group": "Set operations",
        "title": "UNION ALL -- one unified feed from three tables",
        "note": "Combines events from inquiries, transactions and reviews into a single timeline.",
        "sql": """
SELECT 'INQUIRY' AS kind, TO_CHAR(created_at, 'YYYY-MM-DD') AS on_date FROM inquiries
UNION ALL
SELECT 'DEAL',    TO_CHAR(txn_date,   'YYYY-MM-DD')         FROM transactions
UNION ALL
SELECT 'REVIEW',  TO_CHAR(review_date,'YYYY-MM-DD')         FROM reviews
ORDER BY on_date DESC
LIMIT 15
""",
    },
    {
        "group": "Set operations",
        "title": "Set difference with NOT IN vs IN",
        "note": "Segments customers based on whether they saved properties, inquired, or both.",
        "sql": """
SELECT 'Saved but never inquired' AS segment, COUNT(*) AS customers
  FROM favorites
 WHERE user_id NOT IN (SELECT customer_id FROM inquiries)
UNION ALL
SELECT 'Both saved and inquired', COUNT(*)
  FROM favorites
 WHERE user_id IN (SELECT customer_id FROM inquiries)
""",
    },
    # --------------------------------------------------------- PostgreSQL specifics
    {
        "group": "PostgreSQL features",
        "title": "LIMIT and OFFSET pagination",
        "note": "High-performance native PostgreSQL pagination.",
        "sql": """
SELECT property_id, title, price
  FROM properties
 ORDER BY price DESC
 LIMIT 3 OFFSET 3
""",
    },
    {
        "group": "PostgreSQL features",
        "title": "Row generator using UNION ALL",
        "note": "Manufactures ratings 1-5 so star counts of zero still appear on charts.",
        "sql": """
SELECT stars.rating,
       (SELECT COUNT(*) FROM reviews r WHERE r.rating = stars.rating) AS reviews
  FROM (
      SELECT 1 AS rating UNION ALL
      SELECT 2 UNION ALL
      SELECT 3 UNION ALL
      SELECT 4 UNION ALL
      SELECT 5
  ) stars
 ORDER BY stars.rating DESC
""",
    },
    {
        "group": "PostgreSQL features",
        "title": "CASE expression and COALESCE",
        "note": "Clean conditional formatting and NULL substitution in standard SQL.",
        "sql": """
SELECT title,
       CASE listing_type WHEN 'SALE' THEN 'For sale' ELSE 'To let' END AS offer,
       COALESCE(CAST(year_built AS VARCHAR), 'unknown')                AS built,
       CASE WHEN bedrooms >= 5 THEN 'large'
            WHEN bedrooms >= 3 THEN 'medium'
            ELSE 'small' END                                           AS size_band
  FROM properties
 LIMIT 10
""",
    },
    {
        "group": "PostgreSQL features",
        "title": "Date and string formatting",
        "note": "TO_CHAR, EXTRACT, CONCAT, and CHAR_LENGTH.",
        "sql": """
SELECT CONCAT(title, ' (', city_name, ')')              AS title_with_city,
       CHAR_LENGTH(title)                               AS title_chars,
       TO_CHAR(p.created_at, 'FMDay, FMMonth FMDD, YYYY') AS listed_on,
       ROUND((EXTRACT(epoch FROM (NOW() - p.created_at)) / 86400.0 / 30.4)::numeric, 1) AS months_listed,
       TO_CHAR(p.created_at, 'YYYY-MM')                 AS listing_month
  FROM properties p
  JOIN cities c ON c.city_id = p.city_id
 LIMIT 8
""",
    },
    # ------------------------------------------------------- stored routines
    {
        "group": "Stored routines & triggers",
        "title": "Calling PostgreSQL stored functions from SQL",
        "note": "fn_agent_total_sales and fn_agent_avg_rating are PostgreSQL stored functions.",
        "sql": """
SELECT u.full_name,
       fn_agent_total_sales(a.agent_id) AS total_sales,
       fn_agent_avg_rating(a.agent_id)  AS avg_rating
  FROM agents a
  JOIN users u ON u.user_id = a.agent_id
 ORDER BY total_sales DESC
""",
    },
    {
        "group": "Stored routines & triggers",
        "title": "Stored function fn_months_listed",
        "note": "Calculates fractional months on market from database timestamps.",
        "sql": """
SELECT property_id, title, fn_months_listed(property_id) AS months_listed
  FROM properties
 ORDER BY months_listed DESC
 LIMIT 8
""",
    },
    {
        "group": "Stored routines & triggers",
        "title": "Querying view v_agent_performance",
        "note": "Hides correlated aggregations behind an easy-to-query view.",
        "sql": """
SELECT agent_name, total_listings, closed_listings,
       total_sales_value, total_commission, avg_rating
  FROM v_agent_performance
 ORDER BY total_sales_value DESC
""",
    },
    {
        "group": "Stored routines & triggers",
        "title": "Trigger-written audit trail",
        "note": "Every row in audit_log is populated automatically by PostgreSQL triggers.",
        "sql": """
SELECT log_id, table_name, action, record_id, changed_by,
       SUBSTRING(change_details FROM 1 FOR 60) AS details,
       TO_CHAR(changed_at, 'YYYY-MM-DD HH24:MI:SS') AS changed_at
  FROM audit_log
 ORDER BY log_id DESC
 LIMIT 12
""",
    },
    # ------------------------------------------------------- data dictionary
    {
        "group": "Information schema",
        "title": "Table constraints in information_schema",
        "note": "Verifies Primary Keys, Foreign Keys, and Unique constraints registered in PostgreSQL.",
        "sql": """
SELECT table_name, constraint_type, COUNT(*) AS constraint_count
  FROM information_schema.table_constraints
 WHERE table_schema = 'public'
 GROUP BY table_name, constraint_type
 ORDER BY table_name, constraint_type
""",
    },
    {
        "group": "Information schema",
        "title": "Inventory of tables, routines and triggers",
        "note": "A complete count of schema objects read directly from PostgreSQL's data dictionary.",
        "sql": """
SELECT 'TABLE / VIEW' AS object_type, COUNT(*) AS object_count
  FROM information_schema.tables
 WHERE table_schema = 'public'
UNION ALL
SELECT 'STORED ROUTINE', COUNT(*)
  FROM information_schema.routines
 WHERE routine_schema = 'public'
UNION ALL
SELECT 'TRIGGER', COUNT(*)
  FROM information_schema.triggers
 WHERE trigger_schema = 'public'
""",
    },
    {
        "group": "Information schema",
        "title": "Trigger inventory",
        "note": "Every trigger registered on the schema, including timing and event.",
        "sql": """
SELECT trigger_name, event_object_table AS table_name, action_timing, event_manipulation AS triggering_event
  FROM information_schema.triggers
 WHERE trigger_schema = 'public'
 ORDER BY event_object_table, trigger_name
""",
    },
    {
        "group": "Information schema",
        "title": "Indexes backing foreign keys and filters",
        "note": "Indexes ensuring fast search and efficient join performance.",
        "sql": """
SELECT tablename AS table_name, indexname AS index_name,
       CASE WHEN indexdef LIKE '%UNIQUE INDEX%' THEN 'UNIQUE' ELSE 'NON-UNIQUE' END AS uniqueness
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename IN ('properties','inquiries','transactions','property_images')
 ORDER BY tablename, indexname
""",
    },
]


@router.get("/database")
def showcase(request: Request):
    """Run every demo and render the SQL beside its result."""
    auth.require_login(request)

    results = []
    for demo in DEMOS:
        sql = demo["sql"].strip()
        entry = {**demo, "sql": sql, "rows": [], "columns": [],
                 "row_count": 0, "error": None}
        try:
            rows = db.query(sql)
            entry["rows"] = rows[:25]
            entry["row_count"] = len(rows)
            entry["columns"] = list(rows[0].keys()) if rows else []
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc).splitlines()[0]
        results.append(entry)

    groups: list[str] = []
    for demo in DEMOS:
        if demo["group"] not in groups:
            groups.append(demo["group"])

    return render(request, "showcase.html", results=results, groups=groups)
