# Cancer Survivorship: Care Patterns & Outcomes Atlas

An interactive healthcare data-science portfolio project for exploring five cancer cohorts independently, auditing recorded care, and evaluating time-aware prediction models. The project is designed to make the analysis inspectable: visitors can see how cohort definitions, missing data, model evaluation, and source limitations shape the conclusions.

## What a first-time visitor should take away

This project analyzes five supplied cancer studies: Brain, Breast, Prostate, Skin, and Liver. They remain separate because their source files and available fields differ. Four coursework extracts have no usable stage field; only the separate Liver extract includes a summary-stage field. The dashboard therefore does not quietly fill in missing stage or merge incompatible cohorts.

The analysis describes recorded treatment patterns and evaluates whether selected patient and tumor descriptors predict historical surgery coding. It also compares later-year all-cause survival predictions with a cohort baseline. These are exploratory results from the supplied files. The most important conclusion is a boundary: these data and models do not establish which treatment works best for an individual. Treatment codes are incomplete, and factors that influence treatment choice are not captured well enough for a causal treatment-benefit claim.

The source files, patient-level rows, individual predictions, and local runtime outputs are confidential and are not included here. With the dataset owner’s approval, this repository publishes one specific set of whole-cohort results: the [approved aggregate results report](docs/RESULTS_SUMMARY.md). The report contains no raw records or subgroup breakdowns. The public demo values are synthetic and have no clinical meaning.

## Explore the dashboard

**Public interactive demo:** [Open the Cancer Patient Atlas](https://kashishchaudhari.github.io/cancer-survivorship/). This GitHub Pages site is built from invented fixtures only. It contains no supplied dataset or real-data results; individual profile scoring is disabled. The real-data dashboard and its outputs remain local.

Run the project locally with authorized source files to explore:

- age and recorded-sex distributions, treatment-timing histograms, cumulative distributions, and box plots with standard deviation, variance, median, and IQR;
- separate surgery, radiation, and chemotherapy coding views, plus age-by-grade and (Liver only) stage-by-age views;
- all-cause Kaplan–Meier curves with confidence bands, follow-up distributions, and subgroup horizon tables;
- later-year survival-model evaluation against a cohort baseline, including IPCW Brier scores, calibration, and subgroup concordance;
- a separate surgery-recording model for each study, evaluated against test-set prevalence with average precision, ROC AUC, Brier score, and calibration.

Filters apply only to the selected cancer. Small descriptive counts are suppressed. Model outputs describe a historical code pattern, not a treatment recommendation, prognosis, or clinical risk score.

## How the project compares with published guidance

This is a methods comparison, not a head-to-head performance benchmark. Published models use different populations, endpoints, predictors, and validation settings, so their AUC or other scores cannot be compared fairly with this project's private, internal results. The project follows several good practices—explicit cohorts and endpoints, temporal holdout, baseline comparisons, calibration, and clear data limitations—but it is **not** externally validated or ready for clinical use. It does not establish clinical utility or treatment benefit. See [the literature and methods comparison](docs/LITERATURE_CONTEXT.md) for the alignment and gaps.

The reporting checklist in [TRIPOD+AI](https://www.bmj.com/content/385/bmj-2023-078378) and appraisal questions in [PROBAST+AI](https://www.bmj.com/content/388/bmj-2024-082505) are useful references for prediction-model studies. SEER's [treatment-data limitations](https://seer.cancer.gov/data-software/documentation/seerstat/nov2025/treatment-limitations-nov2025.html) explain why recorded treatment and timing fields require cautious interpretation.

## Data and clinical boundaries

The four coursework archives are `BrainCancerProjectSpring2025.rar`, `BreatCancerProjectSpring2025.rar`, `ProstateCancerProject2025.rar`, and `SkinCancerProjectSpring2025.rar`. A fifth study reads `RawLiverCancer.txt` from the user's local source folder and can verify its SHA-256 against the matching member in the supplied ZIP. Source files are read in place and preserved. Patient IDs and individual prediction rows stay in local memory; model files and aggregate JSON stay under ignored `.runtime/`.

The four coursework archives do not contain a usable cancer-stage field. Their stage filters are disabled and stage is excluded from those models; grade is not a substitute. The separate Liver extract includes `Combined Summary Stage (2004+)`; its stage filter and model apply only to that study. The surgery model predicts historical source coding among known `00` and `01–90` surgery codes. Unknown/other codes are excluded. Area income is not personal income, and recorded treatment categories do not confirm that an unrecorded treatment was not received.

The data contain cancer-patient records, not a verified survivor-only population. Results describe internal evaluation of the supplied coursework extracts. They are not causal treatment effects, validated population estimates, or clinical recommendations. The [approved aggregate report](docs/RESULTS_SUMMARY.md) is the specific public disclosure. See the [dataset card](docs/DATASET_CARD.md) and [treatment model study design](docs/TREATMENT_MODEL.md) for detailed provenance, fields, targets, splits, and limitations.

## Run locally

Use Python dependencies locked in `uv.lock`. Replace the example paths with the approved local folder and original ZIP paths:

```powershell
uv sync --locked
uv run python scripts/patient_studies.py --folder "C:\approved\Datasets" --zip "C:\approved\Datasets.zip" --output .runtime/patient-studies
uv run python scripts/build_patient_site.py --source .runtime/patient-studies --target .runtime/patient-site
uv run python scripts/patient_server.py --site .runtime/patient-site --models .runtime/patient-studies/models --port 8766
```

The folder must contain the four `.rar` archives and `RawLiverCancer.txt`. The server binds to `127.0.0.1`. Its research APIs accept small profile requests, do not log request bodies, and load models from local runtime storage.

To run a fully invented demonstration without source-data access:

```powershell
uv run python scripts/patient_studies.py --synthetic --output .runtime/patient-demo
uv run python scripts/build_patient_site.py --source .runtime/patient-demo --target .runtime/patient-demo-site
uv run python scripts/patient_server.py --site .runtime/patient-demo-site --models .runtime/patient-demo/models --port 8766
```

Every demo page labels invented values. They have no clinical meaning.

## Quality checks

```powershell
uv sync --locked
uv run python -m pytest -q
uv run python scripts/check_repository_privacy.py
```

GitHub Actions runs tests and invented fixtures only. A separate deployment workflow publishes the synthetic static dashboard; it never accesses source archives or real-data outputs. The wider [portfolio brief](docs/PORTFOLIO_PLAN.md) explains how this Atlas stays distinct from the survivorship suicide-outcome analysis.
