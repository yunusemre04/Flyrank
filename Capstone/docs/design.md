# Design doc (Phase 1)

**Problem.** Match each blog post to the right image from a ~46-image library by meaning, and refuse when no image is good enough.

**Data model.** `images` (+`image_tags`, `image_vectors`), `posts` (+`post_vectors`), `suggestions` (guard verdict + review state),
`jobs`, `cost_entries`. Indexes: image status/subject/category, tag (kind,value), suggestion (post_id, rank) and unique (post,image), cost created_at.

**Tag schema.** `{subject, category, attributes[], caption, confidence}` validated by Pydantic; invalid -> retry with feedback -> `failed`.

**Matching strategy.** Embed `caption + tags` for images and `title + body` for posts into one space; rank by cosine.

**Guard rules.** Confidence floor, similarity threshold (tuned on the eval set), and a subject/category check against a small taxonomy. All failures are collected into the explanation.

**API surface.** See README. Layers: models/db, services/jobs, HTTP.

**Non-goal.** No frontend, no image search engine, no model comparison, no large corpus.
