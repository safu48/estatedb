-- ============================================================================
--  EstateDB  |  05_procedures.sql
--  Stored program units for PostgreSQL:
--    * Functions: fn_agent_total_sales, fn_agent_avg_rating, fn_property_count,
--                 fn_months_listed, datediff (helper).
--    * Procedures / Functions: sp_record_sale (validation + transaction),
--                              sp_update_inquiry_status (status workflow).
-- ============================================================================

-- ----------------------------------------------------------------------------
--  Total value of all deals closed by an agent.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_agent_total_sales(p_agent_id INT)
RETURNS DECIMAL(14,2) AS $$
DECLARE
    v_total DECIMAL(14,2);
BEGIN
    SELECT COALESCE(SUM(sale_price), 0)
      INTO v_total
      FROM transactions
     WHERE agent_id = p_agent_id;
    RETURN v_total;
END;
$$ LANGUAGE plpgsql STABLE;

-- ----------------------------------------------------------------------------
--  Average customer rating for an agent (0 when never reviewed).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_agent_avg_rating(p_agent_id INT)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    v_avg DECIMAL(3,2);
BEGIN
    SELECT COALESCE(ROUND(AVG(rating)::numeric, 2), 0)
      INTO v_avg
      FROM reviews
     WHERE agent_id = p_agent_id;
    RETURN v_avg;
END;
$$ LANGUAGE plpgsql STABLE;

-- ----------------------------------------------------------------------------
--  Count properties, optionally filtered by status.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_property_count(p_status VARCHAR)
RETURNS INT AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM properties
     WHERE p_status IS NULL OR status = p_status;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- ----------------------------------------------------------------------------
--  How many months a property has been listed.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_months_listed(p_property_id INT)
RETURNS DECIMAL(5,1) AS $$
DECLARE
    v_created TIMESTAMP;
BEGIN
    SELECT created_at INTO v_created
      FROM properties
     WHERE property_id = p_property_id;
    IF v_created IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN ROUND((EXTRACT(epoch FROM (NOW() - v_created)) / 86400.0 / 30.4375)::numeric, 1);
END;
$$ LANGUAGE plpgsql STABLE;

-- ----------------------------------------------------------------------------
--  Compatibility helper: datediff in days
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION datediff(t1 TIMESTAMP, t2 TIMESTAMP)
RETURNS INT AS $$
BEGIN
    RETURN (t1::date - t2::date);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION date_add(d DATE, i INTERVAL)
RETURNS TIMESTAMP AS $$
BEGIN
    RETURN d + i;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION date_sub(d DATE, i INTERVAL)
RETURNS TIMESTAMP AS $$
BEGIN
    RETURN d - i;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ----------------------------------------------------------------------------
--  Record a sale or rental: validates rules, inserts transaction, and returns
--  the new transaction id.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_record_sale(
    p_property_id INT,
    p_buyer_id    INT,
    p_sale_price  DECIMAL(12,2),
    p_txn_type    VARCHAR(10)
)
RETURNS INT AS $$
DECLARE
    v_agent_id INT;
    v_status VARCHAR(12);
    v_txn_id INT;
BEGIN
    -- Find property and verify existence
    SELECT agent_id, status
      INTO v_agent_id, v_status
      FROM properties
     WHERE property_id = p_property_id;

    IF v_agent_id IS NULL THEN
        RAISE EXCEPTION 'Property does not exist.';
    END IF;

    IF v_status IN ('SOLD', 'RENTED') THEN
        RAISE EXCEPTION 'Property is already closed (SOLD or RENTED).';
    END IF;

    IF p_sale_price <= 0 THEN
        RAISE EXCEPTION 'Sale price must be positive.';
    END IF;

    IF p_txn_type NOT IN ('SALE', 'RENT') THEN
        RAISE EXCEPTION 'Type must be SALE or RENT.';
    END IF;

    INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type)
    VALUES (p_property_id, p_buyer_id, v_agent_id, p_sale_price, p_txn_type)
    RETURNING transaction_id INTO v_txn_id;

    RETURN v_txn_id;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
--  Move an inquiry through its status workflow with validation.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_update_inquiry_status(
    p_inquiry_id INT,
    p_status     VARCHAR(20)
)
LANGUAGE plpgsql AS $$
BEGIN
    IF p_status NOT IN ('NEW', 'CONTACTED', 'SCHEDULED', 'CLOSED') THEN
        RAISE EXCEPTION 'Invalid inquiry status value.';
    END IF;

    UPDATE inquiries
       SET status = p_status
     WHERE inquiry_id = p_inquiry_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Inquiry not found.';
    END IF;
END;
$$;
