"""Seed report.db with ~200 random orders. Safe to run twice (deletes first)."""
import random
from datetime import date, timedelta

from db import get_conn, init_schema

PRODUCTS = ["Laptop Stand", "USB-C Hub", "Mechanical Keyboard", "Webcam", "Desk Lamp", "Mouse Pad"]
CUSTOMERS = ["Ayse", "Mehmet", "Elif", "Can", "Zeynep", "Burak", "Selin", "Emre", "Deniz", "Yusuf"]


def seed(n=200):
    conn = get_conn()
    init_schema(conn)
    conn.execute("DELETE FROM orders")
    today = date.today()
    rows = [
        (
            random.choice(CUSTOMERS),
            random.choice(PRODUCTS),
            round(random.uniform(5, 200), 2),
            (today - timedelta(days=random.randint(0, 29))).isoformat(),
        )
        for _ in range(n)
    ]
    conn.executemany(
        "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"orders in db: {count}")
    conn.close()


if __name__ == "__main__":
    seed()
