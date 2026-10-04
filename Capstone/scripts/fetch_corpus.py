"""Download images listed in data/corpus_manifest.csv that have a source_url filled in.

Fill `source_url` (direct image link), `photographer`, and keep the license note, using only Unsplash/Pexels
photos. Run on YOUR machine; this repo does not ship third-party photos.
"""
import csv
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    out = ROOT / "data" / "images"
    out.mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    for row in csv.DictReader(open(ROOT / "data" / "corpus_manifest.csv", encoding="utf-8")):
        if not row["source_url"]:
            skipped += 1
            continue
        dest = out / row["filename"]
        if dest.exists():
            continue
        r = httpx.get(row["source_url"], follow_redirects=True, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        done += 1
        print("downloaded", dest.name)
    print(f"{done} downloaded, {skipped} rows still have no source_url", file=sys.stderr)


if __name__ == "__main__":
    main()
