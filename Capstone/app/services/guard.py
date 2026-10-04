"""The mismatch guard: the best-ranked candidate can still be wrong. Collect EVERY failed check so the
explanation is complete, then approve only if nothing failed."""
from dataclasses import dataclass, field


@dataclass
class Decision:
    approved: bool
    reasons: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)


def evaluate(*, similarity: float, confidence: float | None, flagged: bool, image_subject: str | None,
             image_category: str | None, image_caption: str | None, post_subjects: dict, tax, settings) -> Decision:
    codes, reasons = [], []

    def fail(code: str, msg: str) -> None:
        codes.append(code)
        reasons.append(msg)

    conf = confidence if confidence is not None else 0.0
    if flagged or conf < settings.confidence_min:
        fail("LOW_CONFIDENCE", f"Image classification confidence {conf:.2f} is below {settings.confidence_min:.2f}; flagged for human review")

    threshold = settings.similarity_threshold + (0.0 if post_subjects else settings.unknown_subject_margin)
    if similarity < threshold:
        extra = "" if post_subjects else " (raised because the post's subject is not in the taxonomy)"
        fail("LOW_SIMILARITY", f"Semantic similarity {similarity:.2f} is below the threshold {threshold:.2f}{extra}")

    if post_subjects:
        expected = " or ".join(sorted(post_subjects))
        post_cats = sorted({tax.category_of(s) for s in post_subjects})
        img_sub = tax.canonicalize(image_subject) or tax.canonicalize(image_caption)
        img_cat = tax.category_of(img_sub) or (image_category or "").lower() or None
        if img_sub is None:
            if img_cat and img_cat not in post_cats:
                fail("CATEGORY_MISMATCH", f"Category mismatch: expected {'/'.join(post_cats)} ({expected}), detected {img_cat} ('{image_subject}')")
            else:
                fail("SUBJECT_UNVERIFIED", f"Cannot confirm the image shows {expected}: detected subject '{image_subject}' is not recognised")
        elif img_sub not in post_subjects:
            if img_cat in post_cats:
                fail("SUBJECT_MISMATCH", f"{img_cat.title()} category mismatch: expected {expected}, detected {img_sub}")
            else:
                fail("CATEGORY_MISMATCH", f"Category mismatch: expected {'/'.join(post_cats)} ({expected}), detected {img_cat} ({img_sub})")

    return Decision(approved=not codes, reasons=reasons, codes=codes)
