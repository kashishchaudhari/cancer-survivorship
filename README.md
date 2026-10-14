# Cancer Survivorship: Care Patterns & Outcomes Atlas

The Cancer Patient Atlas turns the supplied Brain, Breast, Prostate, and Skin CancerProject 2025 archives plus the stage-bearing Liver raw extract into five independent studies. Each cancer has its own populations, treatment coding, follow-up analysis, and model evaluation; the app never pools them into one misleading score.

## Explore the atlas

The local interactive dashboard includes:

- cohort-filtered age and recorded-sex distributions, timing histograms, cumulative distributions, and box plots with standard deviation, variance, median, and IQR;
- separate surgery, radiation, and chemotherapy coding views, including an age-by-grade heatmap;
- all-cause Kaplan–Meier curves with confidence bands, follow-up distributions, and subgroup horizon tables;
- patient-disjoint, temporal survival-model evaluation with a cohort baseline, IPCW Brier scores, calibration, and subgroup concordance;
- a separate temporal model for each cancer that predicts whether primary-site surgery was recorded among known surgery codes, compared with the test-set prevalence baseline and a calibration plot.

Filters act on the selected cancer study. Counts below 11 are suppressed in the descriptive views. Hover a chart mark for its displayed denominator and values. Every model and population is specific to its selected cancer archive.

## Data and clinical boundaries

The four coursework archives are `BrainCancerProjectSpring2025.rar`, `BreatCancerProjectSpring2025.rar`, `ProstateCancerProject2025.rar`, and `SkinCancerProjectSpring2025.rar`. A fifth study reads `RawLiverCancer.txt` from the same local source folder and verifies its SHA-256 against the matching member in the supplied ZIP. The pipeline fingerprints the coursework text members and compares them with their matching raw members when given the ZIP. Source files are read in place and preserved. Patient IDs and individual prediction rows stay in local memory; model files and aggregate JSON stay under ignored `.runtime/`.

**The four coursework archives do not contain a usable cancer stage field.** Their stage filters are disabled and stage is excluded from those models; grade is not a substitute. The separate Liver extract includes `Combined Summary Stage (2004+)`; its stage filter and model apply within the Liver study, and missing/unknown values stay visible as such. The surgery model predicts historical source coding among known `00` and `01–90` surgery codes. It estimates neither treatment effectiveness nor what treatment someone should receive. Treatment selection depends on tumor characteristics, health, preferences, and other factors missing from these files. Unknown/other surgery codes are excluded from that model. Radiation and chemotherapy views describe recorded categories only.

The data contain cancer-patient records, not a verified survivor-only population. Results describe internal evaluation of the supplied coursework extracts. They are not clinical recommendations, causal treatment effects, or validated population estimates. Confirm the dataset's data-use terms before sharing any data-derived result. This repo is configured for code and invented test fixtures only; it does not deploy a dashboard, upload build artifacts, or contain real results.

The exact surgery-model target, temporal splits, stage behavior, survival model, and causal limits are documented in [the treatment model study design](docs/TREATMENT_MODEL.md). The broader [portfolio brief](docs/PORTFOLIO_PLAN.md) explains how this Atlas stays separate from the survivorship suicide-outcome analysis.

## Build locally

Use Python dependencies locked in `uv.lock`. On Windows, replace the example paths with the approved local folder and original ZIP paths:

```powershell
uv sync --locked
uv run python scripts/patient_studies.py --folder "C:\approved\Datasets" --zip "C:\approved\Datasets.zip" --output .runtime/patient-studies
uv run python scripts/build_patient_site.py --source .runtime/patient-studies --target .runtime/patient-site
uv run python scripts/patient_server.py --site .runtime/patient-site --models .runtime/patient-studies/models --port 8766
```

The folder must contain the four `.rar` archives and `RawLiverCancer.txt`. The server binds to `127.0.0.1`. Its research APIs accept small profile requests, do not log request bodies, and load models from local runtime storage.

For a fully invented demonstration with no source-data access:

```powershell
uv run python scripts/patient_studies.py --synthetic --output .runtime/patient-demo
uv run python scripts/build_patient_site.py --source .runtime/patient-demo --target .runtime/patient-demo-site
uv run python scripts/patient_server.py --site .runtime/patient-demo-site --models .runtime/patient-demo/models --port 8766
```

Every page labels the invented values. They have no clinical meaning.

## Quality checks

```powershell
uv sync --locked
uv run python -m pytest -q
uv run python scripts/check_repository_privacy.py
```

GitHub Actions runs code tests and invented fixtures only. It has no upload or Pages deployment step.
