import dataclasses

import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.schemas import ImageTags
from app.services import guard
from app.taxonomy import load_taxonomy

GOOD = {"subject": "Red Fox", "category": "animal", "attributes": ["orange fur"], "caption": "A red fox in a forest", "confidence": 0.94}


def test_valid_tags_are_normalised():
    t = ImageTags.model_validate(GOOD)
    assert t.subject == "red fox"


@pytest.mark.parametrize("patch", [{"confidence": 1.5}, {"confidence": -0.1}, {"subject": "  "}, {"caption": ""}, {"confidence": "high"}])
def test_invalid_tags_rejected(patch):
    with pytest.raises(ValidationError):
        ImageTags.model_validate({**GOOD, **patch})


def test_missing_field_rejected():
    bad = {k: v for k, v in GOOD.items() if k != "confidence"}
    with pytest.raises(ValidationError):
        ImageTags.model_validate(bad)


def _eval(post_subjects, subject, category="animal", sim=0.9, conf=0.93, flagged=False, **kw):
    s = get_settings()
    tax = load_taxonomy(s.taxonomy_path)
    return guard.evaluate(similarity=sim, confidence=conf, flagged=flagged, image_subject=subject, image_category=category,
                          image_caption=f"photo of {subject}", post_subjects=post_subjects, tax=tax, settings=kw.get("settings", s))


def test_wolf_on_fox_post_is_rejected_with_explanation():
    d = _eval({"red fox": 5}, "gray wolf", sim=0.95)  # even with a HIGH similarity the guard refuses
    assert not d.approved and "SUBJECT_MISMATCH" in d.codes
    assert d.reasons[0] == "Animal category mismatch: expected red fox, detected gray wolf"


def test_cross_category_mismatch():
    d = _eval({"red fox": 5}, "pizza", category="food")
    assert "CATEGORY_MISMATCH" in d.codes


def test_synonyms_are_accepted():
    assert _eval({"red fox": 5}, "Vulpes vulpes").approved
    assert _eval({"red fox": 5}, "european fox cub").approved


def test_low_confidence_and_low_similarity():
    assert "LOW_CONFIDENCE" in _eval({"red fox": 5}, "red fox", conf=0.3).codes
    assert "LOW_SIMILARITY" in _eval({"red fox": 5}, "red fox", sim=0.2).codes


def test_unknown_post_subject_is_stricter():
    s = get_settings()
    just_above = s.similarity_threshold + 0.01
    assert not _eval({}, "red fox", sim=just_above).approved
    assert _eval({}, "red fox", sim=s.similarity_threshold + s.unknown_subject_margin + 0.01).approved


def test_multi_subject_post_accepts_either():
    assert _eval({"red fox": 3, "gray wolf": 3}, "gray wolf").approved
    assert not _eval({"red fox": 3, "gray wolf": 3}, "deer").approved


def test_unrecognised_image_subject_is_not_trusted():
    d = _eval({"red fox": 5}, "canid thing", category="animal")
    assert "SUBJECT_UNVERIFIED" in d.codes


def test_taxonomy_counts_aliases_once():
    tax = load_taxonomy(get_settings().taxonomy_path)
    assert tax.count("red fox", "Vulpes vulpes were seen; foxes too") == 2
