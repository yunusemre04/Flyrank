"""Measure top-1 precision on the labeled set (data/eval.json). Uses stored vectors: no provider calls.

  python -m scripts.eval                # print metrics
  python -m scripts.eval --sweep        # try similarity thresholds and recommend one
  python -m scripts.eval --write-readme # paste the headline number between the README markers
"""
import argparse
import dataclasses
import fnmatch
import json
import re

from sqlalchemy import select

from app import db
from app.config import ROOT, get_settings
from app.models import Post
from app.services import ranking
from app.taxonomy import load_taxonomy


def evaluate(session, settings, tax, items: list[dict]) -> dict:
    pos = neg = raw_ok = ok = suggested_pos = abstained_neg = wrong_suggestions = 0
    misses = []
    for it in items:
        post = session.scalar(select(Post).where(Post.slug == it["post"]))
        if post is None:
            raise SystemExit(f"eval references unknown post '{it['post']}' (run scripts.seed first)")
        res = ranking.rank_post(session, post, settings, tax)
        match = lambda fn: bool(fn) and any(fnmatch.fnmatch(fn, pat) for pat in it["correct_images"])
        suggested = res.best.image.filename if res.best else None
        if it["correct_images"]:
            pos += 1
            raw_ok += bool(res.ranked) and match(res.ranked[0].image.filename)
            if suggested:
                suggested_pos += 1
            if match(suggested):
                ok += 1
            else:
                if suggested:
                    wrong_suggestions += 1
                misses.append({"post": it["post"], "suggested": suggested, "reasons": res.reasons[:2]})
        else:
            neg += 1
            if suggested is None:
                abstained_neg += 1
            else:
                wrong_suggestions += 1
                misses.append({"post": it["post"], "suggested": suggested, "reasons": ["should have abstained"]})
    return {
        "labeled_posts": pos, "negative_posts": neg,
        "top1_precision": round(ok / pos, 4) if pos else None,  # headline: first guard-approved suggestion is the labeled image
        "top1_precision_unguarded": round(raw_ok / pos, 4) if pos else None,  # raw similarity rank-1, no guard
        "precision_when_suggesting": round(ok / suggested_pos, 4) if suggested_pos else None,
        "abstention_on_negatives": f"{abstained_neg}/{neg}",
        "wrong_suggestions": wrong_suggestions, "misses": misses,
        "similarity_threshold": settings.similarity_threshold,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--write-readme", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    db.configure(s.database_url)
    tax = load_taxonomy(s.taxonomy_path)
    items = json.load(open(s.eval_path, encoding="utf-8"))
    with db.new_session() as session:
        if args.sweep:
            print("threshold  top1  prec_when_suggesting  wrong  abstain_neg")
            rows = []
            for t in [round(0.30 + 0.05 * i, 2) for i in range(14)]:
                r = evaluate(session, dataclasses.replace(s, similarity_threshold=t), tax, items)
                print(f"{t:<10} {r['top1_precision']!s:<5} {r['precision_when_suggesting']!s:<21} {r['wrong_suggestions']:<6} {r['abstention_on_negatives']}")
                rows.append((t, (-r["wrong_suggestions"], r["top1_precision"] or 0)))
            top = max(k for _, k in rows)
            plateau = [t for t, k in rows if k == top]
            print(f"\nrecommended SIMILARITY_THRESHOLD={plateau[len(plateau) // 2]} "
                  f"(middle of the plateau with fewest wrong suggestions, then highest top-1: {plateau[0]}..{plateau[-1]})")
            return
        r = evaluate(session, s, tax, items)
    print(json.dumps(r, indent=2))
    if args.write_readme:
        block = (f"<!-- EVAL:START -->\n**Top-1 precision: {r['top1_precision']:.1%}** on {r['labeled_posts']} labeled posts "
                 f"(unguarded rank-1: {r['top1_precision_unguarded']:.1%}; precision when suggesting: {r['precision_when_suggesting']:.1%}; "
                 f"abstained correctly on {r['abstention_on_negatives']} no-image posts; threshold {r['similarity_threshold']}).\n<!-- EVAL:END -->")
        p = ROOT / "README.md"
        p.write_text(re.sub(r"<!-- EVAL:START -->.*?<!-- EVAL:END -->", lambda _: block, p.read_text(), flags=re.S))
        print("README.md updated")


if __name__ == "__main__":
    main()
