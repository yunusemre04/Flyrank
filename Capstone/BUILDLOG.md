# BUILDLOG: AI usage log

Honesty is graded, perfection is not. Keep this current as you work.

## Where AI helped
- Claude generated the initial scaffold from the capstone brief: FastAPI app, SQLAlchemy models + Alembic migration, providers
  (Gemini/Ollama REST + an offline mock), guard, ranking, batch job, eval script, tests.

## Where AI was wrong / what was fixed
- Tests caught a bug in the generated code: a forced `/check` pruned the post's other pending suggestions; fixed with `prune=False`.
- _Add your own: things you found wrong or changed while running against the real Gemini/Ollama._

## What I changed myself
- _TODO: corpus choice, taxonomy edits, threshold from `--sweep`, anything you rewrote._

## Lines I can explain (evaluator picks 2-3)
- _TODO: read `services/guard.py`, `services/ranking.py`, `jobs.py::_process_image` until you can walk through them._
