"""
============================================================================
E-COMMERCE DATABASE MANAGEMENT SYSTEM (Enterprise Admin & Analytics Portal)
Academic DBMS Capstone Project
============================================================================
Students / Authors:
  - Nisha Rathi (24BYB0137)
  - Anshul Gupta (24BYB0149)

Technical Stack:
  - PostgreSQL 14+ (3NF Engine-level constraints, PL/pgSQL triggers & procedures)
  - Streamlit (Production Python Frontend)
  - psycopg2 & SQLAlchemy (Raw SQL execution & ORM connection pooling)
  - scikit-learn & pandas (RFM Customer Segmentation with K-Means)
============================================================================
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Import RFM Segmentation pipeline
from rfm_segmentation import perform_kmeans_clustering, upsert_customer_segments

# Load environment configuration
load_dotenv()

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="E-Commerce DBMS Portal | Nisha Rathi & Anshul Gupta",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBMS_Portal")

# ============================================================================
# DATABASE CONNECTION & UTILITY FUNCTIONS
# ============================================================================
DEFAULT_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ecommerce_db"
)

def get_connection(db_url: str):
    """Establishes a raw psycopg2 connection."""
    return psycopg2.connect(db_url)

def execute_raw_sql(db_url: str, sql: str, params: tuple = None) -> None:
    """Executes a DDL or DML script on PostgreSQL."""
    conn = get_connection(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

def query_dataframe(db_url: str, sql: str, params: tuple = None) -> pd.DataFrame:
    """Executes a SELECT query and returns a pandas DataFrame."""
    conn = get_connection(db_url)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

def test_db_connection(db_url: str) -> Tuple[bool, str]:
    """Tests the PostgreSQL connection and returns status."""
    try:
        conn = get_connection(db_url)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
        conn.close()
        return True, ver
    except Exception as e:
        return False, str(e)

def run_script_file(db_url: str, filepath: str) -> Tuple[bool, str]:
    """Reads an SQL file and executes it on the target PostgreSQL database."""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        conn = get_connection(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(content)
        conn.close()
        return True, f"Successfully executed `{os.path.basename(filepath)}`."
    except Exception as e:
        return False, f"Error executing `{os.path.basename(filepath)}`: {str(e)}"

# ============================================================================
# SIDEBAR: CONFIGURATION & DATABASE MANAGEMENT
# ============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/database.png", width=64)
    st.title("DBMS Controller")
    st.caption("PostgreSQL Engine & Analytics Admin")

    st.markdown("---")
    st.subheader("🎓 Academic Metadata")
    st.markdown(
        """
        **Project**: E-Commerce DBMS  
        **Team Members**:  
        • **Nisha Rathi** (`24BYB0137`)  
        • **Anshul Gupta** (`24BYB0149`)  
        **Architecture**: 3NF Normalized, PL/pgSQL Triggers, K-Means ML
        """
    )

    st.markdown("---")
    st.subheader("⚙️ Database Connection")
    db_url_input = st.text_input(
        "PostgreSQL Connection URI",
        value=os.getenv("DATABASE_URL", DEFAULT_DB_URL),
        type="password",
        help="Format: postgresql://username:password@hostname:5432/dbname"
    )

    is_connected, db_message = test_db_connection(db_url_input)
    if is_connected:
        st.success("🟢 Connected to PostgreSQL")
        st.caption(f"Engine: {db_message.split(',')[0]}")
    else:
        st.error("🔴 PostgreSQL Disconnected")
        st.caption("Ensure PostgreSQL is active on port 5432.")
        with st.expander("Diagnostic details"):
            st.code(db_message)

    st.markdown("---")
    st.subheader("🛠️ Engine Scripts Runner")
    st.caption("Execute DDL, business logic triggers, and seed data directly in PostgreSQL:")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("1. Schema", use_container_width=True, disabled=not is_connected):
            success, msg = run_script_file(db_url_input, "schema.sql")
            if success:
                st.toast(msg, icon="✅")
            else:
                st.error(msg)

    with col_btn2:
        if st.button("2. Logic", use_container_width=True, disabled=not is_connected):
            success, msg = run_script_file(db_url_input, "procedures_triggers.sql")
            if success:
                st.toast(msg, icon="⚡")
            else:
                st.error(msg)

    col_btn3, col_btn4 = st.columns(2)
    with col_btn3:
        if st.button("3. Seed", use_container_width=True, disabled=not is_connected):
            success, msg = run_script_file(db_url_input, "seed.sql")
            if success:
                st.toast(msg, icon="🌱")
            else:
                st.error(msg)

    with col_btn4:
        if st.button("🚀 Init All", type="primary", use_container_width=True, disabled=not is_connected):
            with st.spinner("Executing full pipeline (Schema -> Logic -> Seed)..."):
                s1, m1 = run_script_file(db_url_input, "schema.sql")
                s2, m2 = run_script_file(db_url_input, "procedures_triggers.sql")
                s3, m3 = run_script_file(db_url_input, "seed.sql")
                if s1 and s2 and s3:
                    st.success("Entire database pipeline executed successfully!")
                    st.rerun()
                else:
                    st.error(f"Execution failed:\n{m1}\n{m2}\n{m3}")


# ============================================================================
# MAIN APPLICATION HEADER
# ============================================================================
st.title("🛒 E-Commerce Database Management System")
st.markdown(
    """
    **Enterprise PostgreSQL Engine with PL/pgSQL Triggers, Stored Procedures, and Unsupervised ML Analytics**  
    *Developers: Nisha Rathi (`24BYB0137`) & Anshul Gupta (`24BYB0149`)*
    """
)
st.markdown("---")

if not is_connected:
    st.warning("⚠️ **PostgreSQL Server is Currently Unreachable**")
    st.info(
        """
        ### Quick Start Instructions to Launch PostgreSQL:
        1. **Option A: Docker Compose (Instant 1-Command Setup)**
           ```bash
           docker compose up -d
           ```
        2. **Option B: Local PostgreSQL Service**
           - Start your PostgreSQL service (`pg_ctl` or Windows Services).
           - Create the database: `CREATE DATABASE ecommerce_db;`
           - Configure `.env` or paste your connection string in the sidebar:
             `postgresql://postgres:postgres@localhost:5432/ecommerce_db`
        3. Once connected, click **🚀 Init All** in the left sidebar to execute `schema.sql`, `procedures_triggers.sql`, and `seed.sql`.
        """
    )
    st.stop()


# ============================================================================
# TABS INTERFACE
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Admin Dashboard & Alerts",
    "🛒 Place Order (Test Triggers)",
    "❌ Cancel Order (Stock Restore)",
    "📈 Sales Reports & Spend",
    "🧠 RFM K-Means Segmentation",
    "🔬 Schema & Live SQL Console"
])


# ============================================================================
# TAB 1: EXECUTIVE ADMIN DASHBOARD & INVENTORY ALERTS
# ============================================================================
with tab1:
    st.header("Executive Admin Dashboard")
    st.caption("Live operational metrics derived directly from normalized 3NF PostgreSQL tables.")

    # High-level Metrics
    try:
        metrics_df = query_dataframe(
            db_url_input,
            """
            SELECT
                (SELECT COUNT(*) FROM products) AS total_products,
                (SELECT COUNT(*) FROM customers) AS total_customers,
                (SELECT COUNT(*) FROM orders) AS total_orders,
                (SELECT COALESCE(SUM(total_amount), 0.00) FROM orders WHERE status != 'Cancelled') AS gross_revenue,
                (SELECT COUNT(*) FROM products WHERE stock_qty < 25) AS low_stock_count;
            """
        )
        row = metrics_df.iloc[0]

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("📦 Total Products", f"{int(row['total_products']):,}")
        m2.metric("👥 Total Customers", f"{int(row['total_customers']):,}")
        m3.metric("🧾 Total Orders", f"{int(row['total_orders']):,}")
        m4.metric("💰 Gross Revenue", f"${float(row['gross_revenue']):,.2f}")
        m5.metric("⚠️ Low Stock (<25)", f"{int(row['low_stock_count']):,}", delta="-Alert" if row['low_stock_count'] > 0 else "OK")
    except Exception as e:
        st.error(f"Error fetching KPI metrics: {e}")

    st.markdown("---")
    col_dash_left, col_dash_right = st.columns([3, 2])

    with col_dash_left:
        st.subheader("📦 Product Catalog & Live Inventory")
        try:
            prod_df = query_dataframe(
                db_url_input,
                """
                SELECT
                    p.product_id,
                    p.product_name,
                    c.category_name,
                    p.price,
                    p.stock_qty,
                    CASE
                        WHEN p.stock_qty = 0 THEN 'OUT OF STOCK'
                        WHEN p.stock_qty < 25 THEN 'LOW STOCK'
                        ELSE 'IN STOCK'
                    END AS stock_status
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                ORDER BY p.stock_qty ASC, p.product_id ASC;
                """
            )

            # Highlight low stock
            def highlight_stock(val):
                if val == 'OUT OF STOCK':
                    return 'background-color: #ff4d4d; color: white; font-weight: bold;'
                elif val == 'LOW STOCK':
                    return 'background-color: #ffeaa7; color: black; font-weight: bold;'
                return ''

            st.dataframe(
                prod_df.style.applymap(highlight_stock, subset=['stock_status']),
                use_container_width=True,
                height=350
            )
        except Exception as e:
            st.error(f"Error loading catalog: {e}")

    with col_dash_right:
        st.subheader("🚨 Inventory Depletion Alerts (< 25 units)")
        try:
            alerts_df = query_dataframe(
                db_url_input,
                """
                SELECT product_id, product_name, stock_qty, price
                FROM products
                WHERE stock_qty < 25
                ORDER BY stock_qty ASC;
                """
            )
            if alerts_df.empty:
                st.success("🎉 All inventory levels are above the safety replenishment threshold (>= 25 units).")
            else:
                st.warning(f"Found {len(alerts_df)} products requiring immediate replenishment:")
                st.dataframe(alerts_df, use_container_width=True, height=350)
        except Exception as e:
            st.error(f"Error loading stock alerts: {e}")

    st.markdown("---")
    st.subheader("📋 Recent Orders & Payment Settlement Status")
    try:
        orders_df = query_dataframe(
            db_url_input,
            """
            SELECT
                o.order_id,
                o.order_date,
                c.customer_name,
                c.city,
                o.status AS order_status,
                o.total_amount,
                COALESCE(p.method, 'Not Set') AS payment_method,
                COALESCE(p.payment_status, 'None') AS payment_status
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            ORDER BY o.order_id DESC;
            """
        )
        st.dataframe(orders_df, use_container_width=True, height=300)
    except Exception as e:
        st.error(f"Error loading recent orders: {e}")


# ============================================================================
# TAB 2: PLACE ORDER & ENGINE TRIGGER TESTING
# ============================================================================
with tab2:
    st.header("Place Order via Stored Procedure `place_order`")
    st.caption(
        "Demonstrates atomic execution of `place_order(p_customer_id, p_items JSONB)`, "
        "BEFORE INSERT trigger `trg_validate_and_deduct_stock`, and AFTER INSERT trigger `trg_update_order_total`."
    )

    try:
        cust_list = query_dataframe(db_url_input, "SELECT customer_id, customer_name, email FROM customers ORDER BY customer_id ASC;")
        prod_list = query_dataframe(db_url_input, "SELECT product_id, product_name, price, stock_qty FROM products ORDER BY product_id ASC;")

        col_ord_left, col_ord_right = st.columns([1, 1])

        with col_ord_left:
            st.subheader("1. Select Customer")
            cust_options = {f"#{row.customer_id} - {row.customer_name} ({row.email})": row.customer_id for _, row in cust_list.iterrows()}
            selected_cust_label = st.selectbox("Customer", list(cust_options.keys()))
            selected_cust_id = cust_options[selected_cust_label]

            st.subheader("2. Build Shopping Cart Items")
            st.info("💡 **Trigger Test**: Choose a quantity GREATER than stock (e.g. 500) to verify that `trg_validate_and_deduct_stock` blocks the order!")

            if "cart" not in st.session_state:
                st.session_state.cart = []

            prod_options = {f"#{row.product_id} - {row.product_name} (${row.price:.2f} | Stock: {row.stock_qty})": row for _, row in prod_list.iterrows()}
            chosen_prod_label = st.selectbox("Select Product to Add", list(prod_options.keys()))
            chosen_prod = prod_options[chosen_prod_label]

            item_qty = st.number_input("Order Quantity", min_value=1, max_value=1000, value=1, step=1)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if st.button("➕ Add Item to Cart", use_container_width=True):
                    # Check if already in cart
                    existing = next((item for item in st.session_state.cart if item["product_id"] == chosen_prod.product_id), None)
                    if existing:
                        existing["quantity"] += item_qty
                    else:
                        st.session_state.cart.append({
                            "product_id": int(chosen_prod.product_id),
                            "product_name": chosen_prod.product_name,
                            "unit_price": float(chosen_prod.price),
                            "quantity": int(item_qty),
                            "available_stock": int(chosen_prod.stock_qty)
                        })
                    st.rerun()

            with col_c2:
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()

        with col_ord_right:
            st.subheader("3. Current Order Payload (JSONB)")
            if not st.session_state.cart:
                st.write("🛒 *Cart is currently empty. Add products on the left.*")
            else:
                cart_df = pd.DataFrame(st.session_state.cart)
                cart_df["subtotal"] = cart_df["quantity"] * cart_df["unit_price"]
                st.dataframe(cart_df[["product_id", "product_name", "quantity", "unit_price", "subtotal", "available_stock"]], use_container_width=True)

                total_cart_val = cart_df["subtotal"].sum()
                st.markdown(f"### Estimated Total: **${total_cart_val:,.2f}**")

                # Prepare JSONB payload
                items_payload = [
                    {"product_id": item["product_id"], "quantity": item["quantity"], "unit_price": item["unit_price"]}
                    for item in st.session_state.cart
                ]

                with st.expander("Inspect JSONB argument sent to PostgreSQL"):
                    st.json(items_payload)

                if st.button("🚀 Execute `place_order` Stored Procedure", type="primary", use_container_width=True):
                    with st.spinner("Calling PostgreSQL stored procedure..."):
                        conn = get_connection(db_url_input)
                        try:
                            with conn.cursor() as cur:
                                # Call the function wrapper or stored procedure with INOUT
                                json_str = json.dumps(items_payload)
                                cur.execute("SELECT fn_place_order(%s, %s::jsonb);", (selected_cust_id, json_str))
                                generated_order_id = cur.fetchone()[0]

                                # Also insert a default pending payment record
                                cur.execute(
                                    """
                                    INSERT INTO payments (order_id, method, amount, payment_status, payment_date)
                                    VALUES (%s, 'UPI', (SELECT total_amount FROM orders WHERE order_id = %s), 'Completed', CURRENT_TIMESTAMP)
                                    ON CONFLICT (order_id) DO NOTHING;
                                    """,
                                    (generated_order_id, generated_order_id)
                                )
                            conn.commit()

                            st.success(f"🎉 **Order Placed Successfully! Order ID: #{generated_order_id}**")
                            st.info(
                                f"✅ **Trigger 1**: Deducted required quantities from `products.stock_qty`.\n"
                                f"✅ **Trigger 2**: Recalculated `orders.total_amount` directly inside the database."
                            )
                            st.session_state.cart = []
                        except psycopg2.Error as p_err:
                            conn.rollback()
                            st.error(f"🛑 **Database Engine Exception Raised!**\n\n`{p_err.pgerror or str(p_err)}`")
                            st.warning("Notice how PostgreSQL engine constraints/triggers aborted the entire transaction safely!")
                        except Exception as ex:
                            conn.rollback()
                            st.error(f"Application Error: {str(ex)}")
                        finally:
                            conn.close()
    except Exception as e:
        st.error(f"Error loading form data: {e}")


# ============================================================================
# TAB 3: CANCEL ORDER & STOCK RESTORATION
# ============================================================================
with tab3:
    st.header("Cancel Order via Stored Procedure `cancel_order`")
    st.caption("Marks status 'Cancelled', atomically restores all item stock quantities, and marks payment 'Refunded' or 'Failed'.")

    try:
        active_orders = query_dataframe(
            db_url_input,
            """
            SELECT
                o.order_id,
                o.order_date,
                c.customer_name,
                o.status,
                o.total_amount,
                COALESCE(p.payment_status, 'No Payment') AS payment_status
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            WHERE o.status != 'Cancelled'
            ORDER BY o.order_id DESC;
            """
        )

        if active_orders.empty:
            st.info("No active orders eligible for cancellation.")
        else:
            col_cn1, col_cn2 = st.columns([1, 1])
            with col_cn1:
                order_select_dict = {
                    f"Order #{row.order_id} | {row.customer_name} | ${row.total_amount:.2f} ({row.status})": row.order_id
                    for _, row in active_orders.iterrows()
                }
                selected_ord_label = st.selectbox("Select Active Order to Cancel", list(order_select_dict.keys()))
                target_order_id = order_select_dict[selected_ord_label]

                # Fetch line items for this order to see what stock will be restored
                line_items_df = query_dataframe(
                    db_url_input,
                    """
                    SELECT
                        oi.product_id,
                        p.product_name,
                        oi.quantity,
                        oi.unit_price,
                        p.stock_qty AS current_stock_in_db,
                        (p.stock_qty + oi.quantity) AS expected_stock_after_restoration
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.product_id
                    WHERE oi.order_id = %s;
                    """,
                    (target_order_id,)
                )

            with col_cn2:
                st.subheader("Items to be Restored to Inventory")
                st.dataframe(line_items_df, use_container_width=True)

                if st.button("🛑 Execute `cancel_order` Procedure", type="primary", use_container_width=True):
                    conn = get_connection(db_url_input)
                    try:
                        with conn.cursor() as cur:
                            cur.execute("CALL cancel_order(%s);", (target_order_id,))
                        conn.commit()
                        st.success(f"✅ Order #{target_order_id} successfully cancelled!")
                        st.info("Inventory items were atomically incremented back into `products.stock_qty` and payment status updated.")
                        st.rerun()
                    except Exception as ex:
                        conn.rollback()
                        st.error(f"Cancellation error: {ex}")
                    finally:
                        conn.close()
    except Exception as e:
        st.error(f"Error loading cancellation interface: {e}")


# ============================================================================
# TAB 4: SALES REPORTS & LIFETIME SPEND
# ============================================================================
with tab4:
    st.header("Executive Sales Reports & Customer Lifetime Spend")

    col_rep1, col_rep2 = st.columns([1, 1])

    with col_rep1:
        st.subheader("💡 Lifetime Spend Stored Function")
        st.caption("Executes `get_customer_total_spent(p_customer_id)` directly in PostgreSQL:")
        try:
            cust_df = query_dataframe(db_url_input, "SELECT customer_id, customer_name, email FROM customers ORDER BY customer_id ASC;")
            c_dict = {f"#{row.customer_id}: {row.customer_name}": row.customer_id for _, row in cust_df.iterrows()}
            selected_c = st.selectbox("Select Customer", list(c_dict.keys()), key="lifetime_cust_select")
            cid = c_dict[selected_c]

            spent_df = query_dataframe(db_url_input, "SELECT get_customer_total_spent(%s) AS total_spent;", (cid,))
            total_spent = float(spent_df.iloc[0]["total_spent"])

            st.metric(
                label=f"Lifetime Spend for Customer #{cid}",
                value=f"${total_spent:,.2f}"
            )
        except Exception as e:
            st.error(f"Error testing get_customer_total_spent: {e}")

    with col_rep2:
        st.subheader("💳 Sales by Category Breakdown")
        try:
            cat_sales_df = query_dataframe(
                db_url_input,
                """
                SELECT
                    c.category_name,
                    COUNT(DISTINCT oi.order_id) AS orders_count,
                    COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
                    COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS total_revenue
                FROM categories c
                LEFT JOIN products p ON c.category_id = p.category_id
                LEFT JOIN order_items oi ON p.product_id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status != 'Cancelled'
                GROUP BY c.category_name
                ORDER BY total_revenue DESC;
                """
            )
            st.dataframe(cat_sales_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error fetching category sales: {e}")

    st.markdown("---")
    st.subheader("🏆 Top-Selling Products by Revenue")
    try:
        top_prod_df = query_dataframe(
            db_url_input,
            """
            SELECT
                p.product_id,
                p.product_name,
                c.category_name,
                p.price,
                COALESCE(SUM(oi.quantity), 0) AS units_sold,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS gross_sales
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN order_items oi ON p.product_id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status != 'Cancelled'
            GROUP BY p.product_id, p.product_name, c.category_name, p.price
            ORDER BY gross_sales DESC, units_sold DESC;
            """
        )
        st.dataframe(top_prod_df, use_container_width=True, height=300)
    except Exception as e:
        st.error(f"Error loading top products: {e}")

    st.markdown("---")
    st.subheader("⭐ Product Reviews & Customer Sentiment")
    try:
        rev_df = query_dataframe(
            db_url_input,
            """
            SELECT
                r.review_id,
                p.product_name,
                c.customer_name,
                r.rating,
                r.review_text,
                r.review_date
            FROM reviews r
            JOIN products p ON r.product_id = p.product_id
            JOIN customers c ON r.customer_id = c.customer_id
            ORDER BY r.review_date DESC;
            """
        )
        st.dataframe(rev_df, use_container_width=True, height=250)
    except Exception as e:
        st.error(f"Error loading reviews: {e}")


# ============================================================================
# TAB 5: RFM K-MEANS CUSTOMER SEGMENTATION
# ============================================================================
with tab5:
    st.header("Customer Analytics & ML Module: RFM Segmentation")
    st.markdown(
        """
        Uses **Recency, Frequency, and Monetary (RFM)** features extracted directly from PostgreSQL.
        Applies **scikit-learn** `StandardScaler` followed by **K-Means Clustering** ($k=4$) to partition customers into:
        - **Loyal**: Frequent repeat buyers with recent touchpoints.
        - **Big Spender**: Customers generating the highest monetary sales.
        - **At-Risk**: Dormant customers with long recency intervals since their last order.
        - **New**: Recently acquired customers with initial order volume.
        """
    )

    col_rfm1, col_rfm2 = st.columns([3, 1])
    with col_rfm2:
        if st.button("⚡ Run K-Means Clustering Pipeline", type="primary", use_container_width=True):
            with st.spinner("Extracting RFM metrics, scaling, and running K-Means..."):
                conn = get_connection(db_url_input)
                try:
                    from rfm_segmentation import fetch_rfm_data
                    raw_df = fetch_rfm_data(conn)
                    clustered_df = perform_kmeans_clustering(raw_df, n_clusters=4)
                    upsert_customer_segments(conn, clustered_df)
                    st.success("✅ Clustering complete and results upserted to `customer_segments`!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"RFM Pipeline error: {ex}")
                finally:
                    conn.close()

    try:
        # Load current customer_segments
        segments_df = query_dataframe(
            db_url_input,
            """
            SELECT
                cs.customer_id,
                c.customer_name,
                c.city,
                cs.recency_days,
                cs.frequency,
                cs.monetary_value,
                cs.segment_label,
                cs.last_updated
            FROM customer_segments cs
            JOIN customers c ON cs.customer_id = c.customer_id
            ORDER BY cs.monetary_value DESC;
            """
        )

        if segments_df.empty:
            st.info("No segments found in database. Click 'Run K-Means Clustering Pipeline' to compute segments.")
        else:
            # Color badge styling
            def label_color(val):
                colors = {
                    "Big Spender": "background-color: #d4edda; color: #155724; font-weight: bold;",
                    "Loyal": "background-color: #cce5ff; color: #004085; font-weight: bold;",
                    "At-Risk": "background-color: #f8d7da; color: #721c24; font-weight: bold;",
                    "New": "background-color: #fff3cd; color: #856404; font-weight: bold;"
                }
                return colors.get(val, "")

            st.dataframe(
                segments_df.style.applymap(label_color, subset=['segment_label']),
                use_container_width=True
            )

            # Segment distribution chart
            st.subheader("📊 Customer Segment Distribution")
            chart_data = segments_df["segment_label"].value_counts().reset_index()
            chart_data.columns = ["Segment Label", "Customer Count"]

            col_c1, col_c2 = st.columns([1, 1])
            with col_c1:
                st.bar_chart(chart_data.set_index("Segment Label"))

            with col_c2:
                # Segment Summary Statistics
                summary_stats = segments_df.groupby("segment_label").agg(
                    Count=("customer_id", "count"),
                    Avg_Recency=("recency_days", "mean"),
                    Avg_Frequency=("frequency", "mean"),
                    Total_Monetary=("monetary_value", "sum")
                ).reset_index()
                st.dataframe(summary_stats, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading customer segments: {e}")


# ============================================================================
# TAB 6: SCHEMA & LIVE SQL CONSOLE
# ============================================================================
with tab6:
    st.header("PostgreSQL Schema & Interactive SQL Console")
    st.caption("Inspect normalization structure, constraints, triggers, and run ad-hoc queries.")

    st.subheader("Interactive SQL Query Runner")
    custom_query = st.text_area(
        "Enter Raw SQL Query",
        value="SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;",
        height=100
    )

    if st.button("Run SQL Query", type="secondary"):
        try:
            result_df = query_dataframe(db_url_input, custom_query)
            st.success(f"Query returned {len(result_df)} rows:")
            st.dataframe(result_df, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Error: {e}")

    st.markdown("---")
    st.subheader("Database Schema Viewer")
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        selected_tbl = st.selectbox(
            "Select Table to Inspect",
            ["categories", "products", "customers", "orders", "order_items", "payments", "reviews", "customer_segments"]
        )
    with col_t2:
        try:
            cols_df = query_dataframe(
                db_url_input,
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (selected_tbl,)
            )
            st.dataframe(cols_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error fetching columns: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.85em;'>
        DBMS Capstone Project &copy; 2026 | Developed by Nisha Rathi (24BYB0137) & Anshul Gupta (24BYB0149)<br>
        Enforcing 3NF Relational Normalization, PostgreSQL PL/pgSQL Engine Routines, and Scikit-Learn RFM Analytics
    </div>
    """,
    unsafe_allow_html=True
)
