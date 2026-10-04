"""Stage 2 + 3 checkpoint: print the report as JSON, then render reports/test.pdf."""
import json
from pathlib import Path

from render import render_pdf
from report_data import get_report_data

data = get_report_data()
print(json.dumps({k: v for k, v in data.items() if k != "all_orders"}, indent=2))
Path("reports").mkdir(exist_ok=True)
render_pdf(data, "reports/test.pdf")
print("wrote reports/test.pdf")
