from db import get_conn

TOTALS_SQL = "SELECT COUNT(*) AS total_orders, ROUND(COALESCE(SUM(amount), 0), 2) AS total_revenue FROM orders"

TOP_PRODUCTS_SQL = """
SELECT product, COUNT(*) AS orders, ROUND(SUM(amount), 2) AS revenue
FROM orders
GROUP BY product
ORDER BY revenue DESC
LIMIT 5
"""

DAILY_SQL = """
SELECT created_at AS day, COUNT(*) AS orders
FROM orders
WHERE created_at >= date('now', '-6 days')
GROUP BY created_at
ORDER BY created_at
"""

ALL_ORDERS_SQL = "SELECT id, customer, product, amount, created_at FROM orders ORDER BY created_at DESC, id DESC"


def get_report_data():
    conn = get_conn()
    try:
        totals = dict(conn.execute(TOTALS_SQL).fetchone())
        return {
            "totals": totals,
            "top_products": [dict(r) for r in conn.execute(TOP_PRODUCTS_SQL)],
            "orders_per_day": [dict(r) for r in conn.execute(DAILY_SQL)],
            "all_orders": [dict(r) for r in conn.execute(ALL_ORDERS_SQL)],
        }
    finally:
        conn.close()
