-- ============================================================================
--  EstateDB  |  02_tables.sql
--  Tables, constraints (PK / FK / UNIQUE / CHECK / NOT NULL) and indexes.
--  PostgreSQL compliant (SERIAL / BIGSERIAL, TIMESTAMP).
-- ============================================================================

-- ----------------------------------------------------------------------------
--  Lookup tables
-- ----------------------------------------------------------------------------
CREATE TABLE roles (
    role_id     SERIAL PRIMARY KEY,
    role_name   VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE cities (
    city_id     SERIAL PRIMARY KEY,
    city_name   VARCHAR(60) NOT NULL,
    state       VARCHAR(60),
    country     VARCHAR(60) DEFAULT 'USA',
    CONSTRAINT uq_city UNIQUE (city_name, state)
);

CREATE TABLE property_types (
    type_id     SERIAL PRIMARY KEY,
    type_name   VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE amenities (
    amenity_id   SERIAL PRIMARY KEY,
    amenity_name VARCHAR(50) NOT NULL UNIQUE
);

-- ----------------------------------------------------------------------------
--  Users & agents
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    user_id        SERIAL PRIMARY KEY,
    username       VARCHAR(40)  NOT NULL UNIQUE,
    email          VARCHAR(120) NOT NULL UNIQUE,
    password_hash  VARCHAR(200) NOT NULL,
    password_salt  VARCHAR(64)  NOT NULL,
    full_name      VARCHAR(100) NOT NULL,
    phone          VARCHAR(30),
    role_id        INT          NOT NULL,
    is_active      CHAR(1)      DEFAULT 'Y',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_is_active CHECK (is_active IN ('Y', 'N')),
    CONSTRAINT fk_user_role FOREIGN KEY (role_id) REFERENCES roles (role_id)
);

-- One-to-one extension of USERS for people whose role is "Agent".
CREATE TABLE agents (
    agent_id        INT PRIMARY KEY,
    license_no      VARCHAR(40)  NOT NULL UNIQUE,
    agency_name     VARCHAR(100),
    bio             TEXT,
    commission_rate DECIMAL(5,2) DEFAULT 2.50,
    hire_date       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_commission CHECK (commission_rate BETWEEN 0 AND 100),
    CONSTRAINT fk_agent_user FOREIGN KEY (agent_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
--  Properties and their satellite tables
-- ----------------------------------------------------------------------------
CREATE TABLE properties (
    property_id  SERIAL PRIMARY KEY,
    title        VARCHAR(150)   NOT NULL,
    description  TEXT,
    type_id      INT            NOT NULL,
    city_id      INT            NOT NULL,
    agent_id     INT            NOT NULL,
    address      VARCHAR(200),
    price        DECIMAL(12,2)  NOT NULL,
    bedrooms     INT            DEFAULT 0,
    bathrooms    INT            DEFAULT 0,
    area_sqft    DECIMAL(10,2),
    year_built   INT,
    listing_type VARCHAR(10)    NOT NULL,
    status       VARCHAR(12)    DEFAULT 'AVAILABLE',
    featured     CHAR(1)        DEFAULT 'N',
    created_at   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_price        CHECK (price > 0),
    CONSTRAINT ck_listing_type CHECK (listing_type IN ('SALE', 'RENT')),
    CONSTRAINT ck_status       CHECK (status IN ('AVAILABLE','PENDING','SOLD','RENTED')),
    CONSTRAINT ck_featured     CHECK (featured IN ('Y', 'N')),
    CONSTRAINT fk_prop_type    FOREIGN KEY (type_id)  REFERENCES property_types (type_id),
    CONSTRAINT fk_prop_city    FOREIGN KEY (city_id)  REFERENCES cities (city_id),
    CONSTRAINT fk_prop_agent   FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
);

CREATE TABLE property_images (
    image_id    SERIAL PRIMARY KEY,
    property_id INT          NOT NULL,
    image_url   VARCHAR(300) NOT NULL,
    is_primary  CHAR(1)      DEFAULT 'N',
    CONSTRAINT ck_is_primary CHECK (is_primary IN ('Y','N')),
    CONSTRAINT fk_img_prop   FOREIGN KEY (property_id)
        REFERENCES properties (property_id) ON DELETE CASCADE
);

-- Many-to-many bridge between properties and amenities.
CREATE TABLE property_amenities (
    property_id INT NOT NULL,
    amenity_id  INT NOT NULL,
    PRIMARY KEY (property_id, amenity_id),
    CONSTRAINT fk_pa_prop    FOREIGN KEY (property_id)
        REFERENCES properties (property_id) ON DELETE CASCADE,
    CONSTRAINT fk_pa_amenity FOREIGN KEY (amenity_id)
        REFERENCES amenities (amenity_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
--  Activity tables
-- ----------------------------------------------------------------------------
CREATE TABLE inquiries (
    inquiry_id     SERIAL PRIMARY KEY,
    property_id    INT            NOT NULL,
    customer_id    INT            NOT NULL,
    message        VARCHAR(1000),
    preferred_date DATE,
    status         VARCHAR(12)    DEFAULT 'NEW',
    created_at     TIMESTAMP      DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_inq_status
        CHECK (status IN ('NEW','CONTACTED','SCHEDULED','CLOSED')),
    CONSTRAINT fk_inq_prop FOREIGN KEY (property_id)
        REFERENCES properties (property_id) ON DELETE CASCADE,
    CONSTRAINT fk_inq_cust FOREIGN KEY (customer_id)
        REFERENCES users (user_id)
);

CREATE TABLE transactions (
    transaction_id    SERIAL PRIMARY KEY,
    property_id       INT           NOT NULL,
    buyer_id          INT           NOT NULL,
    agent_id          INT           NOT NULL,
    sale_price        DECIMAL(12,2) NOT NULL,
    commission_amount DECIMAL(12,2),
    txn_type          VARCHAR(10)   NOT NULL,
    txn_date          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_txn_price CHECK (sale_price > 0),
    CONSTRAINT ck_txn_type  CHECK (txn_type IN ('SALE','RENT')),
    CONSTRAINT fk_txn_prop  FOREIGN KEY (property_id) REFERENCES properties (property_id),
    CONSTRAINT fk_txn_buyer FOREIGN KEY (buyer_id)    REFERENCES users (user_id),
    CONSTRAINT fk_txn_agent FOREIGN KEY (agent_id)    REFERENCES agents (agent_id)
);

CREATE TABLE reviews (
    review_id   SERIAL PRIMARY KEY,
    agent_id    INT            NOT NULL,
    customer_id INT            NOT NULL,
    rating      INT            NOT NULL,
    comments    VARCHAR(1000),
    review_date TIMESTAMP      DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_rating    CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT uq_review    UNIQUE (agent_id, customer_id),
    CONSTRAINT fk_rev_agent FOREIGN KEY (agent_id)    REFERENCES agents (agent_id),
    CONSTRAINT fk_rev_cust  FOREIGN KEY (customer_id) REFERENCES users (user_id)
);

CREATE TABLE favorites (
    user_id     INT NOT NULL,
    property_id INT NOT NULL,
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, property_id),
    CONSTRAINT fk_fav_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_fav_prop FOREIGN KEY (property_id)
        REFERENCES properties (property_id) ON DELETE CASCADE
);

-- Written to by the audit triggers in 03_triggers.sql.
CREATE TABLE audit_log (
    log_id         BIGSERIAL PRIMARY KEY,
    table_name     VARCHAR(40),
    action         VARCHAR(10),
    record_id      BIGINT,
    changed_by     VARCHAR(60),
    change_details VARCHAR(500),
    changed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
--  Secondary indexes
-- ----------------------------------------------------------------------------
CREATE INDEX idx_prop_city    ON properties (city_id);
CREATE INDEX idx_prop_type    ON properties (type_id);
CREATE INDEX idx_prop_agent   ON properties (agent_id);
CREATE INDEX idx_prop_status  ON properties (status);
CREATE INDEX idx_prop_price   ON properties (price);
CREATE INDEX idx_prop_listing ON properties (listing_type);
CREATE INDEX idx_inq_prop     ON inquiries (property_id);
CREATE INDEX idx_inq_cust     ON inquiries (customer_id);
CREATE INDEX idx_txn_agent    ON transactions (agent_id);
CREATE INDEX idx_txn_date     ON transactions (txn_date);
CREATE INDEX idx_img_prop     ON property_images (property_id);
