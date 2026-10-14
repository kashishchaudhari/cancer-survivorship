# Survivorship Observatory

A healthcare data-science research project combining reproducible ETL, cohort auditing, internal model evaluation, survival analysis, and an interactive dashboard.

**Confidential-data policy:** patient data, derived tables, figures, workbooks, and data-derived reports remain local. This repository is intended to contain code and methodological documentation only. No data redistribution or real-data hosting is authorized. A private repository alone does not grant permission to upload a restricted dataset.

## Understand the data

Read the [dataset card](docs/DATASET_CARD.md) for the source structure, analysis populations, field meanings, missingness, selection rules, and limits. Read the [privacy policy](docs/DATA_PRIVACY.md) before preparing any GitHub repository.

The full supplied ZIP contains raw cancer extracts and separate coursework-derived workbooks. Raw extracts support patient grouping; sampled workbooks are a separate analysis population. Complete supplied files do not establish that we hold the full SEER registry or a representative population sample.

## Code validation with invented fixtures

```powershell
uv sync --locked
uv run python -m pytest -q
uv run python scripts/generate_demo_data.py --output .runtime/demo-data
uv run python scripts/build_dashboard_static.py --source .runtime/demo-data --target .runtime/demo-site --synthetic
node scripts/check_dashboard.mjs --site .runtime/demo-site
uv run python scripts/check_repository_privacy.py
```

Fixtures are generated entirely from invented constants and are labeled **SYNTHETIC TEST DATA**. They test software behavior; their model metrics and survival values have no clinical meaning. GitHub Actions runs code and synthetic checks only. It does not upload artifacts or deploy GitHub Pages.

## Authorized local research

Run the extraction and care-equity scripts against your approved local archive. No identifiers or patient-level predictions are written to dashboard tables. After reviewing local aggregate inputs:

```powershell
uv run python scripts/build_dashboard_static.py --source dashboard/data --target .runtime/site
node scripts/check_dashboard.mjs --site .runtime/site
uv run python -m http.server 8765 --bind 127.0.0.1 --directory .runtime/site
```

Open http://127.0.0.1:8765. This server binds to localhost. The real-data dashboard is confidential and must not be publicly hosted. Its Plotly library is retrieved from a CDN; chart inputs are loaded locally, and the current code does not upload them. Follow your institution's approved environment requirements.

Independent source validation is available through `scripts/validate_source_data.py --archive "C:\path\to\Datasets.zip"`. Detailed evidence, including hashes, source counts, cohort reconciliation and independent survival calculations, is written to ignored local runtime files.

## Reliability boundaries

Code tests and independent calculation checks do not establish clinical validity, causal treatment effects, or national population risk estimates. Model configuration comparisons are exploratory; the existing test fold has been reused. Treatment timing is not a treatment recommendation, and an area's income is not an individual's earnings. All research findings are internal evaluation of the supplied dataset.

## Existing Git history

The original local history contains derived results. Removing them from the current index does not erase that history. Do not push the existing repository. Prepare a fresh, code-only repository from the reviewed export and verify its contents before publication. No history rewrite or remote upload is performed by this project.
