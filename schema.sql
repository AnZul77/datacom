-- ============================================================================
-- E-COMMERCE DATABASE MANAGEMENT SYSTEM (PostgreSQL DDL)
-- Academic DBMS Project
-- Students / Authors:
--   - Nisha Rathi (24BYB0137)
--   - Anshul Gupta (24BYB0149)
-- Database Engine: PostgreSQL 14+ / Strictly Compliant with Third Normal Form (3NF)
-- ============================================================================

-- Drop tables in reverse-dependency order to support clean idempotent executions
DROP TABLE IF EXISTS customer_segments CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================================================
-- 1. CATEGORIES TABLE
-- Entity representing product taxonomy (normalized to 1NF, 2NF & 3NF)
-- ============================================================================
CREATE TABLE categories (
    category_id     SERIAL PRIMARY KEY,
    category_name   VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. PRODUCTS TABLE
-- Catalog of inventory items with price, current stock, and category reference
-- ============================================================================
CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(150) NOT NULL,
    category_id     INT NOT NULL,
    price           NUMERIC(10, 2) NOT NULL,
    stock_qty       INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_products_price_positive
        CHECK (price > 0),
    CONSTRAINT chk_products_stock_non_negative
        CHECK (stock_qty >= 0)
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_name ON products(product_name);

-- ============================================================================
-- 3. CUSTOMERS TABLE
-- Stores demographic, contact, and registration details of shoppers
-- ============================================================================
CREATE TABLE customers (
    customer_id     SERIAL PRIMARY KEY,
    customer_name   VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    city            VARCHAR(100),
    join_date       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_city ON customers(city);
CREATE INDEX idx_customers_email ON customers(email);

-- ============================================================================
-- 4. CARTS TABLE
-- Maintains the active persistent shopping session per customer (1:1 relation)
-- ============================================================================
CREATE TABLE carts (
    cart_id         SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL UNIQUE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_carts_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_carts_customer ON carts(customer_id);

-- ============================================================================
-- 5. CART_ITEMS TABLE
-- Associative table resolving M:N relationship between Cart and Product
-- ============================================================================
CREATE TABLE cart_items (
    cart_item_id    SERIAL PRIMARY KEY,
    cart_id         INT NOT NULL,
    product_id      INT NOT NULL,
    quantity        INT NOT NULL DEFAULT 1,
    CONSTRAINT fk_cart_items_cart
        FOREIGN KEY (cart_id)
        REFERENCES carts(cart_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT uq_cart_product
        UNIQUE (cart_id, product_id),
    CONSTRAINT chk_cart_items_quantity_positive
        CHECK (quantity > 0)
);

CREATE INDEX idx_cart_items_cart ON cart_items(cart_id);
CREATE INDEX idx_cart_items_product ON cart_items(product_id);

-- ============================================================================
-- 6. ORDERS TABLE
-- High-level purchase master records with status tracking and running total
-- ============================================================================
CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL,
    order_date      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(20) NOT NULL DEFAULT 'Placed',
    total_amount    NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_orders_status
        CHECK (status IN ('Placed', 'Shipped', 'Delivered', 'Cancelled')),
    CONSTRAINT chk_orders_total_non_negative
        CHECK (total_amount >= 0)
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);

-- ============================================================================
-- 7. ORDER_ITEMS TABLE
-- Normalized line items linking products to orders; enforces composite uniqueness
-- and captures point-in-time unit pricing snapshot.
-- ============================================================================
CREATE TABLE order_items (
    order_item_id   SERIAL PRIMARY KEY,
    order_id        INT NOT NULL,
    product_id      INT NOT NULL,
    quantity        INT NOT NULL,
    unit_price      NUMERIC(10, 2) NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT uq_order_product
        UNIQUE (order_id, product_id),
    CONSTRAINT chk_order_items_quantity_positive
        CHECK (quantity > 0),
    CONSTRAINT chk_order_items_price_positive
        CHECK (unit_price > 0)
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- ============================================================================
-- 8. PAYMENTS TABLE
-- 1-to-1 payment transaction linked to each order with payment lifecycle state
-- ============================================================================
CREATE TABLE payments (
    payment_id      SERIAL PRIMARY KEY,
    order_id        INT NOT NULL UNIQUE,
    method          VARCHAR(30) NOT NULL,
    amount          NUMERIC(12, 2) NOT NULL,
    payment_status  VARCHAR(20) NOT NULL DEFAULT 'Pending',
    payment_date    TIMESTAMPTZ,
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT chk_payments_method
        CHECK (method IN ('Credit Card', 'Debit Card', 'UPI', 'Net Banking', 'Cash on Delivery')),
    CONSTRAINT chk_payments_amount_positive
        CHECK (amount > 0),
    CONSTRAINT chk_payments_status
        CHECK (payment_status IN ('Pending', 'Completed', 'Failed', 'Refunded'))
);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(payment_status);

-- ============================================================================
-- 9. REVIEWS TABLE
-- Customer feedback on purchased items; 1 review per customer-product pair
-- ============================================================================
CREATE TABLE reviews (
    review_id       SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL,
    product_id      INT NOT NULL,
    rating          INT NOT NULL,
    review_text     VARCHAR(500),
    review_date     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reviews_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT uq_customer_product_review
        UNIQUE (customer_id, product_id),
    CONSTRAINT chk_reviews_rating_range
        CHECK (rating BETWEEN 1 AND 5)
);

CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_customer ON reviews(customer_id);

-- ============================================================================
-- 10. CUSTOMER_SEGMENTS TABLE
-- Analytics segmentation store (Recency, Frequency, Monetary + Cluster label)
-- ============================================================================
CREATE TABLE customer_segments (
    customer_id     INT PRIMARY KEY,
    recency_days    INT NOT NULL,
    frequency       INT NOT NULL,
    monetary_value  NUMERIC(12, 2) NOT NULL,
    segment_label   VARCHAR(30) NOT NULL,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_segments_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT chk_segments_recency
        CHECK (recency_days >= 0),
    CONSTRAINT chk_segments_frequency
        CHECK (frequency >= 0),
    CONSTRAINT chk_segments_monetary
        CHECK (monetary_value >= 0),
    CONSTRAINT chk_segments_label
        CHECK (segment_label IN ('Loyal', 'Big Spender', 'At-Risk', 'New'))
);

CREATE INDEX idx_customer_segments_label ON customer_segments(segment_label);
