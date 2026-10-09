-- ============================================================================
--  EstateDB  |  03_triggers.sql
--  PostgreSQL Triggers & Trigger Functions:
--    (A) Audit triggers: record changes to PROPERTIES, USERS, INQUIRIES and
--        TRANSACTIONS into AUDIT_LOG.
--    (B) Business-rule triggers: auto-calculate a transaction's commission
--        and automatically flip the sold/rented status of the related property.
-- ============================================================================

-- --- (A1) Audit triggers on PROPERTIES ---------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_properties_after_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
    VALUES ('PROPERTIES', 'INSERT', NEW.property_id, CURRENT_USER,
            CONCAT('Listed "', NEW.title, '" at ', NEW.price));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_after_insert ON properties;
CREATE TRIGGER trg_properties_after_insert
AFTER INSERT ON properties
FOR EACH ROW
EXECUTE FUNCTION fn_trg_properties_after_insert();


CREATE OR REPLACE FUNCTION fn_trg_properties_after_update()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
    VALUES ('PROPERTIES', 'UPDATE', NEW.property_id, CURRENT_USER,
            CONCAT('status ', OLD.status, '->', NEW.status, '; price ', OLD.price, '->', NEW.price));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_after_update ON properties;
CREATE TRIGGER trg_properties_after_update
AFTER UPDATE ON properties
FOR EACH ROW
EXECUTE FUNCTION fn_trg_properties_after_update();


CREATE OR REPLACE FUNCTION fn_trg_properties_after_delete()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
    VALUES ('PROPERTIES', 'DELETE', OLD.property_id, CURRENT_USER,
            CONCAT('Removed "', OLD.title, '"'));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_after_delete ON properties;
CREATE TRIGGER trg_properties_after_delete
AFTER DELETE ON properties
FOR EACH ROW
EXECUTE FUNCTION fn_trg_properties_after_delete();


-- --- (A2) Audit triggers on USERS --------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_users_after_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
    VALUES ('USERS', 'INSERT', NEW.user_id, CURRENT_USER,
            CONCAT('Account "', NEW.username, '" created in role ', NEW.role_id));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_after_insert ON users;
CREATE TRIGGER trg_users_after_insert
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION fn_trg_users_after_insert();


CREATE OR REPLACE FUNCTION fn_trg_users_after_update()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.is_active <> NEW.is_active OR OLD.role_id <> NEW.role_id OR OLD.email <> NEW.email) THEN
        INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
        VALUES ('USERS', 'UPDATE', NEW.user_id, CURRENT_USER,
                CONCAT('active ', COALESCE(OLD.is_active, '?'), '->', COALESCE(NEW.is_active, '?'),
                       '; role ', OLD.role_id, '->', NEW.role_id));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_after_update ON users;
CREATE TRIGGER trg_users_after_update
AFTER UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_trg_users_after_update();


-- --- (A3) Audit trigger on INQUIRIES -----------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_inquiries_after_update()
RETURNS TRIGGER AS $$
BEGIN
    IF (COALESCE(OLD.status, '-') <> COALESCE(NEW.status, '-')) THEN
        INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
        VALUES ('INQUIRIES', 'UPDATE', NEW.inquiry_id, CURRENT_USER,
                CONCAT('status ', OLD.status, '->', NEW.status));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_inquiries_after_update ON inquiries;
CREATE TRIGGER trg_inquiries_after_update
AFTER UPDATE ON inquiries
FOR EACH ROW
EXECUTE FUNCTION fn_trg_inquiries_after_update();


-- --- (A4) Audit trigger on TRANSACTIONS --------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_txn_after_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, changed_by, change_details)
    VALUES ('TRANSACTIONS', 'INSERT', NEW.transaction_id, CURRENT_USER,
            CONCAT(NEW.txn_type, ' of property ', NEW.property_id,
                   ' for ', NEW.sale_price,
                   ', commission ', COALESCE(CAST(NEW.commission_amount AS VARCHAR), 'none')));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_txn_after_insert ON transactions;
CREATE TRIGGER trg_txn_after_insert
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_trg_txn_after_insert();


-- --- (B1) Auto-commission calculation for TRANSACTIONS -----------------------
CREATE OR REPLACE FUNCTION fn_trg_txn_before_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_rate DECIMAL(5,2);
BEGIN
    IF NEW.commission_amount IS NULL THEN
        SELECT commission_rate INTO v_rate
          FROM agents
         WHERE agent_id = NEW.agent_id;
        NEW.commission_amount := ROUND((NEW.sale_price * v_rate / 100)::numeric, 2);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_txn_before_insert ON transactions;
CREATE TRIGGER trg_txn_before_insert
BEFORE INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_trg_txn_before_insert();


-- --- (B2) Automatically update property status on sale or rent ---------------
CREATE OR REPLACE FUNCTION fn_trg_txn_after_insert_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE properties
       SET status = CASE WHEN NEW.txn_type = 'SALE' THEN 'SOLD' ELSE 'RENTED' END
     WHERE property_id = NEW.property_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_txn_after_insert_status ON transactions;
CREATE TRIGGER trg_txn_after_insert_status
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_trg_txn_after_insert_status();
