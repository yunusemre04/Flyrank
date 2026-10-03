"""Runs evals/cases.json against a running instance of the API and prints a score.

Usage:
    python evals/run_eval.py [--base-url http://127.0.0.1:8000]
"""

import argparse
import json
from pathlib import Path

import httpx

CASES_PATH = Path(__file__).resolve().parent / "cases.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    correct = 0
    failures = []

    with httpx.Client(base_url=args.base_url, timeout=60.0) as client:
        for case in cases:
            response = client.post("/enrich", json=case["input"])
            if response.status_code != 200:
                failures.append(f"{case['id']}: HTTP {response.status_code} — {response.text}")
                continue

            body = response.json()
            actual = body.get("category")
            expected = case["expected_category"]
            if actual == expected:
                correct += 1
            else:
                failures.append(f"{case['id']}: expected '{expected}', got '{actual}'")

    total = len(cases)
    print(f"Score: {correct}/{total} on category")
    if failures:
        print("Failed cases:")
        for line in failures:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
