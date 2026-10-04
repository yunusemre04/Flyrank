from datetime import date
from html import escape

CSS = """
@page { margin: 18mm 14mm; }
body { font-family: Helvetica, Arial, sans-serif; color: #1f2937; font-size: 11px; }
h1 { margin: 0 0 4px; font-size: 24px; }
h2 { margin: 24px 0 8px; font-size: 15px; }
.sub { color: #6b7280; margin-bottom: 16px; }
.cards { display: flex; gap: 12px; }
.card { flex: 1; background: #eef2ff; border-radius: 8px; padding: 12px; }
.card .n { font-size: 22px; font-weight: bold; color: #3730a3; }
table { width: 100%; border-collapse: collapse; }
th { background: #3730a3; color: white; text-align: left; padding: 6px; }
td { padding: 5px 6px; border-bottom: 1px solid #e5e7eb; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
td.num, th.num { text-align: right; }
"""


def _table(headers, rows, num_cols=()):
    head = "".join(
        f'<th class="{"num" if i in num_cols else ""}">{escape(h)}</th>' for i, h in enumerate(headers)
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="{"num" if i in num_cols else ""}">{escape(str(c))}</td>'
            for i, c in enumerate(r)
        )
        + "</tr>"
        for r in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_html(data):
    t = data["totals"]
    top = _table(
        ["Product", "Orders", "Revenue"],
        [(p["product"], p["orders"], f'${p["revenue"]:,.2f}') for p in data["top_products"]],
        num_cols=(1, 2),
    )
    daily = _table(
        ["Day", "Orders"], [(d["day"], d["orders"]) for d in data["orders_per_day"]], num_cols=(1,)
    )
    allo = _table(
        ["ID", "Customer", "Product", "Amount", "Date"],
        [(o["id"], o["customer"], o["product"], f'${o["amount"]:.2f}', o["created_at"]) for o in data["all_orders"]],
        num_cols=(3,),
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<h1>Sales Report</h1>
<div class="sub">Generated {date.today().isoformat()}</div>
<div class="cards">
  <div class="card"><div>Total orders</div><div class="n">{t["total_orders"]}</div></div>
  <div class="card"><div>Total revenue</div><div class="n">${t["total_revenue"]:,.2f}</div></div>
</div>
<h2>Top 5 products by revenue</h2>{top}
<h2>Orders per day (last 7 days)</h2>{daily}
<h2>All orders</h2>{allo}
</body></html>"""


def render_pdf(data, out_path):
    # imported lazily so the rest of the app works without a browser installed
    from playwright.sync_api import sync_playwright

    html = build_html(data)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(out_path), format="A4", print_background=True)
        browser.close()
