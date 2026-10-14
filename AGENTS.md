# Project instructions

Use uv for Python environment and dependency management. Keep pyproject.toml and uv.lock in version control. Run scripts using uv run and verify with uv sync --locked.

Keep patient-level data, raw SEER extracts, prediction rows, and local runtime files out of Git. Preserve original source files. Report model results as internal evaluation of the supplied sampled dataset, not validated clinical or population risk estimates.
