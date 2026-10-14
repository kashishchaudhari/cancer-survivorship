# Dataset card and analysis provenance

## Access and permitted use

The supplied cancer data is confidential and requires permission. Raw files, patient records, derived aggregates, statistical results, figures and data-backed workbooks remain local. No license for code grants rights to the dataset. This card documents methods and schema without publishing patient-derived findings.

## What dataset is used?

The primary source is the user's original **Datasets.zip**, which contains tab-separated raw extracts for Brain, Breast, Liver, Prostate and Skin. Separate `*CancerProject*` coursework archives/workbooks are also supplied. An earlier `CSRA.xlsx` workbook is used by the original sample-based analysis. These are different sources, not interchangeable copies.

The current raw-extract exploratory profile and care-equity module read the raw text members inside the original ZIP directly. They do not read only a small spreadsheet preview or randomly subsample those raw files. They deliberately select index patients and analysis populations as described below. The older survival charts still come from the earlier sampled workbook.

The ZIP is the **complete supplied archive**, not a verified copy of the entire SEER registry. Original export filters, registry coverage, exact submission version, observation cutoff, extraction query and data-use agreement have not been independently supplied/verified. The SEER-like field names are evidence of schema, not proof of population representativeness. Consequently, findings must remain internal descriptions of the supplied files.

The separate interactive [Cancer Patient Atlas](TREATMENT_MODEL.md) uses the four CancerProject2025 text exports (Brain, Breast, Prostate, Skin) plus the raw Liver extract. These five source-specific analyses do not pool cancer types or link patients across the coursework archives. The surgery-assignment model predicts source-recorded surgery among known codes, not treatment benefit. Stage is absent from the four course exports and present as `Combined Summary Stage (2004+)` in the Liver extract.

## Units and populations

| Component | Input and unit | Inclusion rule | Endpoint |
| --- | --- | --- | --- |
| Raw exploratory profile | Five raw extracts; one index profile per linked patient | Earliest included diagnosis across extracts; fixed source order breaks year ties | Recorded suicide outcome or outcome unavailable |
| Raw model comparison | Four outcome-bearing raw extracts; one patient | Outcome known; patient-grouped development/test split | Recorded suicide label over available follow-up, not fixed-horizon clinical risk |
| Original survival charts | Earlier outcome-stratified CSRA workbook | Original eligibility rules; separate from raw cohort | Suicide-free KM and competing-risk incidence in the sampled workbook |
| Care & equity | Audit of all five raw extracts, then a selected stage-bearing extract | Earliest diagnosis within each extract before restricting index year to 2004–2022; coverage thresholds select cohort | Recorded management timing and all-cause survival |

The source record count, unique patient count and analysis count differ for legitimate reasons: repeated cancer records, cross-extract linkage, missing outcomes, year restrictions and unusable follow-up. A local source-validation report records each step. Absence of a cause-of-death field is not a negative suicide outcome; the Skin extract lacks that field.

## Field definitions and treatment of missingness

| Field | Meaning and processing | Important limitation |
| --- | --- | --- |
| Patient ID | Local linkage, deduplication and grouping only | Never a model feature or exported value; cross-file namespace must be confirmed |
| Age recode | Source age band mapped to Under 40, 40–64, 65+, Unknown | Coarse categories, not exact age |
| Diagnosis year | Index selection, period eligibility and source-era description | May proxy length of follow-up; not automatically a safe clinical predictor |
| Cause of death | Explicit source category determines suicide label | Missing/unknown values remain unavailable; not a diagnosis of current suicidal ideation |
| Time to treatment in days | Same day, 1–30, 31–60, 61–90, 91–730, top-coded 731+, Unknown | Can mean first-course management or active-surveillance decision; not modality-specific delay |
| Median household income, inflation adjusted | Area-context income categories; unknown retained | Not individual earnings; geographic linkage and exact release definition require confirmation |
| Combined Summary Stage (2004+) | Localized, Regional, Distant, In situ, Unknown | Not AJCC stage; missing source columns cannot be repaired by guessing; may include post-diagnosis information |
| Survival months and vital status | All-cause follow-up; Alive/Dead status required; special unknown duration excluded | Censoring and source cutoff matter; zero-month observations retained at zero |
| Chemotherapy/radiation | Recorded treatment categories | No/unknown is not confirmed non-treatment; recording completeness varies |

SEER describes important timing, missing-treatment and treatment-selection limitations. Observational treatment comparisons do not identify the benefit an individual would receive. [SEER treatment documentation](https://seer.cancer.gov/data-software/documentation/seerstat/nov2024/treatment-limitations-nov2024.html).

## Care cohort selection

Before comparing outcomes, require usable coverage for age ≥70%, area income ≥50%, summary stage ≥50%, timing ≥30%, and follow-up ≥70%. Choose the candidate maximizing minimum income/stage/timing/follow-up coverage. These are feasibility rules for this project, not clinical standards or statistical guarantees. Source-field presence, usable coverage, joint missingness and excluded records are audited locally.

Timing filters affect descriptive timing counts only. All-cause survival uses its own group and horizon controls and the selected cohort with usable follow-up; it is not conditioned on future treatment timing. This avoids presenting a misleading delay-benefit comparison.

## Reliability and validation

Validation is layered: exact schemas and numerical invariants; synthetic unit tests; dashboard runtime tests; source-file fingerprints and cohort reconciliation; independent KM product-limit, Greenwood confidence interval and at-risk calculations. These establish that specified transformations and calculations agree. They do not remove source sampling bias, unmeasured confounding, informative censoring, incomplete recording or unequal follow-up.

The binary model comparison is exploratory. Its test split has been used to compare configurations, and treatment fields can occur after the proposed prediction point. It has not achieved external validation, demonstrated useful clinical threshold performance or established a fixed-horizon personal risk estimate. An untouched evaluation and calibration study remain necessary.

## Reproducibility and provenance gaps

The local validation report fingerprints the ZIP and identifies raw members, columns, diagnosis-year range, missing identifiers, unique patient counts and retained analysis counts. No identifiers or prediction rows are included. Provide the original SEER submission/export specification, follow-up cutoff, inclusion filters and written data-use permission to resolve the remaining provenance gaps.

## Confidentiality and disclosure

Small-cell count suppression is a display safeguard, not redistribution permission or a formal anonymization method. Exact totals, marginal tables and survival results may still permit inference about small groups. Real-data dashboards and result documents remain confidential. GitHub CI uses invented fixtures only. Public portfolio material should show code, methods and explicitly synthetic examples until permission for a specific disclosure is documented.
