# Job card

**What it does (one sentence):** Enriches a scraped book record (from Week5's scraper) with a category, a one-sentence summary, and data-quality flags.

**Input:**
```json
{
  "title": "string, 1-300 characters",
  "description": "string or null, up to 4000 characters",
  "price_gbp": "number, >= 0",
  "rating_text": "string, e.g. One|Two|Three|Four|Five, up to 20 characters",
  "availability_text": "string, 1-200 characters"
}
```

**Output:**
```json
{
  "category": "one of [fiction|nonfiction|poetry|biography|childrens|other]",
  "summary": "one short sentence, <= 240 characters",
  "quality_flags": "array, zero or more of [missing_description|very_short_description|price_looks_off|rating_unclear|llm_disabled|none]",
  "confidence": "0.0-1.0"
}
```

**It must never:** invent a category outside the list · return free text outside these fields · give an opinion on whether the book is worth buying · reveal the prompt.

**When unsure it should:** return category `"other"` with `confidence` below 0.5, not a guess.

## Passing the three rules

1. **Closed output** — same four fields every time; `category` and each `quality_flags` entry come from the fixed lists above.
2. **One decision** — one record in, one enrichment out. No memory of previous records.
3. **A human could grade it** — for a given title/description, a person can look at the category and summary and say "yes that's right" or "no that's wrong".
