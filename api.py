"""
============================================================================
E-COMMERCE DBMS REST API (FastAPI Backend)
Academic DBMS Capstone Project
============================================================================
Students / Authors:
  - Nisha Rathi (24BYB0137)
  - Anshul Gupta (24BYB0149)
============================================================================
"""

import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from rfm_segmentation import fetch_rfm_data, perform_kmeans_clustering, upsert_customer_segments

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ecommerce_db")

app = FastAPI(
    title="E-Commerce DBMS API",
    description="Academic PostgreSQL Engine & Analytics Backend by Nisha Rathi (24BYB0137) & Anshul Gupta (24BYB0149)",
    version="1.0.0"
)

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

# Pydantic Schemas
class OrderItemPayload(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    unit_price: Optional[float] = Field(default=None, gt=0, description="Optional unit price override")

class PlaceOrderRequest(BaseModel):
    customer_id: int
    items: List[OrderItemPayload]

class CancelOrderRequest(BaseModel):
    order_id: int

@app.get("/health", tags=["Health"])
def health_check():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
        conn.close()
        return {"status": "healthy", "database": "connected", "version": ver}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/api/products", tags=["Products"])
def get_products(db = Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.product_id, p.product_name, c.category_name, p.price, p.stock_qty
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.product_id ASC;
        """)
        return cur.fetchall()

@app.get("/api/inventory/alerts", tags=["Products"])
def get_inventory_alerts(threshold: int = 25, db = Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT product_id, product_name, stock_qty, price
            FROM products
            WHERE stock_qty < %s
            ORDER BY stock_qty ASC;
        """, (threshold,))
        return cur.fetchall()

@app.get("/api/orders", tags=["Orders"])
def get_orders(db = Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                o.order_id, o.order_date, c.customer_name, o.status,
                o.total_amount, p.method AS payment_method, p.payment_status
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            ORDER BY o.order_id DESC;
        """)
        return cur.fetchall()

@app.post("/api/orders/place", tags=["Orders"], status_code=status.HTTP_201_CREATED)
def api_place_order(payload: PlaceOrderRequest, db = Depends(get_db)):
    items_json = json.dumps([item.model_dump(exclude_none=True) for item in payload.items])
    try:
        with db.cursor() as cur:
            cur.execute("SELECT fn_place_order(%s, %s::jsonb);", (payload.customer_id, items_json))
            order_id = cur.fetchone()[0]
            # Create payment record
            cur.execute("""
                INSERT INTO payments (order_id, method, amount, payment_status, payment_date)
                VALUES (%s, 'UPI', (SELECT total_amount FROM orders WHERE order_id = %s), 'Completed', CURRENT_TIMESTAMP)
                ON CONFLICT (order_id) DO NOTHING;
            """, (order_id, order_id))
        db.commit()
        return {"status": "success", "order_id": order_id, "message": "Order placed successfully via stored procedure."}
    except psycopg2.Error as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=e.pgerror or str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders/{order_id}/cancel", tags=["Orders"])
def api_cancel_order(order_id: int, db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("CALL cancel_order(%s);", (order_id,))
        db.commit()
        return {"status": "success", "order_id": order_id, "message": "Order cancelled and stock restored."}
    except psycopg2.Error as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=e.pgerror or str(e))

@app.get("/api/customers/{customer_id}/spend", tags=["Customers"])
def api_get_customer_spend(customer_id: int, db = Depends(get_db)):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT get_customer_total_spent(%s);", (customer_id,))
            spent = cur.fetchone()[0]
        return {"customer_id": customer_id, "total_spent": float(spent)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analytics/rfm-segment", tags=["Analytics & ML"])
def api_run_rfm_segmentation(db = Depends(get_db)):
    try:
        raw_df = fetch_rfm_data(db)
        clustered_df = perform_kmeans_clustering(raw_df, n_clusters=4)
        count = upsert_customer_segments(db, clustered_df)
        return {
            "status": "success",
            "customers_segmented": count,
            "data": clustered_df[[
                "customer_id", "customer_name", "recency_days",
                "frequency", "monetary_value", "segment_label"
            ]].to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
