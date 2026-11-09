# Cancer Care Research Atlas

**Independent healthcare analytics portfolio · Kashish Chaudhari**

[Explore the real-data research dashboard](https://kashishchaudhari.github.io/cancer-survivorship/)
· [Read the whole-cohort report](RESULTS_SUMMARY.md)
· [Inspect five cancer case studies](CASE_STUDIES.md)

## The problem

Cancer source files differ in population, available fields, missingness, and
treatment coding. A useful analyst must establish a trustworthy denominator
before presenting a chart or a prediction metric. This project asks what those
files support, where recording is incomplete, and how well selected demographic
and tumor descriptors predict historical surgery recording.

## What I built

The project joins a reproducible Python research pipeline, documented cohort
definitions, held-out model evaluation, and an interactive public research report.
Brain, Breast, Prostate, Skin, and Liver remain independent studies. The public
report uses actual published cohort-level results; private source records and
individual predictions are not distributed.

The full-feature synthetic dashboard remains available as an engineering demo.
Its invented patient profiles are separate from the real research dashboard.
There is no public patient-level scoring service or live Snowflake pipeline.

## Analyst decisions demonstrated

| Work area | Implementation | Why it matters |
| --- | --- | --- |
| Cohort preparation | Earliest-index selection and source fingerprints | Reconciles source records with study patients |
| Data quality | Explicit timing missingness and field availability | Prevents known-value medians from implying complete coverage |
| Domain interpretation | No/unknown treatment codes remain uncertain | Avoids equating missing records with no treatment |
| Statistical analysis | Independent cohorts; descriptive timing and all-cause survival | Separates research populations and endpoints |
| Evaluation | Patient holdout, development-only cross-validation, AP prevalence baseline, AUC uncertainty, Brier score | Shows model performance in context |
| Delivery | Static interactive report generated from published Markdown tables | Makes values traceable without distributing source records |

## Findings worth discussing in an interview

The published descriptive timing medians range from 0 days in Skin to 49 days in
Prostate, while unknown timing ranges from 27.2% to 57.0%. Those medians therefore
describe calculable, non-top-coded records rather than every patient's experience.
The timing field can include surveillance decisions and is not a reliable
modality-specific measure of waiting time.

Only Liver has a usable summary-stage field in these study sources. The other
four coursework extracts do not. Disabling unsupported stage analyses is an
intentional analytical decision, rather than filling the gap with grade.

In the Liver patient-holdout surgery-recording model, ROC AUC is 0.823 with a
fixed-model bootstrap interval of 0.809–0.836; average precision is 0.601 against
test prevalence of 0.236. The endpoint is recorded surgery among known source
codes. It does not estimate treatment benefit or establish clinical usefulness.
All values above are reproduced from the already-published reports linked here.

## Reproducibility and publication scope

`scripts/build_research_demo.py` reads only `docs/RESULTS_SUMMARY.md` and
`docs/CASE_STUDIES.md`, checks their overlapping values agree, and produces a
small aggregate payload with source-document hashes. CI tests all five studies
under both evaluation designs. Raw files, local paths, model binaries, patient
identifiers, and prediction rows are excluded from this public artifact.

The source data were supplied for coursework/research. The exact SEER submission,
extraction filters, and observation cutoff have not been independently verified;
no release citation is fabricated. The user describes intended journal
publication. Journal acceptance, peer review, independent external validation,
and clinical deployment are not claimed. The author must resolve the source
citation and applicable data-use terms before journal submission or any new
data-derived disclosure.

These are internal evaluations of supplied sampled datasets, not validated
clinical or population risk estimates. This is a portfolio presentation of
research and analytical work, with methodological limitations kept visible.
