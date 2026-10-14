# Cancer Patient Atlas: whole-cohort results

**Disclosure scope:** This update showcases whole-cohort results as requested by the repository owner. The five cancer case studies add whole-cohort evaluation and uncertainty only. Raw files, patient-level records, predictions, local runtime artifacts, and subgroup results remain private; future disclosures require their own authorization.

## Updated patient-holdout evaluation

The requested evaluation update uses a stratified 80/20 patient holdout and development-only cross-validation. Liver is featured in the [case study](LIVER_STUDY.md), with baseline comparisons and a fixed-model bootstrap interval. These are revised internal evaluations of the supplied sampled dataset; the new split is not independent external validation.

| Study | Patient-test n | Test prevalence | Average precision | ROC AUC | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Brain | 2,636 | 0.736 | 0.786 | 0.609 | 0.187 |
| Breast | 28,515 | 0.908 | 0.951 | 0.716 | 0.074 |
| Prostate | 25,156 | 0.368 | 0.544 | 0.695 | 0.209 |
| Skin | 11,304 | 0.929 | 0.942 | 0.568 | 0.066 |
| Liver | 4,074 | 0.236 | 0.601 | 0.823 | 0.133 |

The positive class is recorded surgery among known codes. Stratification is within each independent cohort. Average precision must be interpreted against that cohort's test prevalence. No test metric selects regularization. The temporal results below remain a secondary sensitivity analysis, with different test populations.

## Previously published descriptive and temporal findings

Across the five separate cohorts, the median recorded time-to-treatment ranged from 0 days for Skin to 49 days for Prostate. The share with unknown timing was substantial (27.2%–57.0%), so observed timing summaries describe only records with calculable non-top-coded values. The exploratory surgery-code models had test ROC AUCs from 0.556 to 0.817. These scores measure prediction of historical source coding, not which treatment works best.

## Whole-cohort summaries

| Study | Source rows | Earliest-index patients | Median recorded timing (days) | IQR (days) | SD (days) | Timing unknown (% of index) | Surgery-code test ROC AUC | Brier score | Test n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Brain | 63,337 | 62,983 | 3 | 0–13 | 32.7 | 41.6% | 0.632 | 0.187 | 3,400 |
| Breast | 701,163 | 651,419 | 20 | 1–35 | 30.4 | 29.1% | 0.723 | 0.080 | 38,010 |
| Prostate | 624,498 | 624,327 | 49 | 17–85 | 68.7 | 46.3% | 0.697 | 0.207 | 33,410 |
| Skin | 223,281 | 207,121 | 0 | 0–6 | 23.6 | 27.2% | 0.556 | 0.079 | 15,486 |
| Liver | 64,880 | 64,491 | 42 | 20–72 | 58.7 | 57.0% | 0.817 | 0.139 | 5,578 |

Timing distribution summaries exclude unknown and top-coded 731+ day records. Recorded day zero can reflect source coding or surveillance decisions and should not be interpreted as a universal treatment start. Timing variability differs by cohort; standard deviation and IQR are included because medians alone hide that spread.

## Evaluation design and interpretation

The secondary surgery-code evaluation uses a temporal split: 2010–2013 for development, 2014–2015 for validation, and 2016–2017 as the held-out test period. It predicts whether historical source records contain a known surgery code, among records with known 00 or 01–90 codes; unknown/other codes are excluded. Test-set sample sizes are shown above. AUC assesses ranking and Brier score assesses probability error; neither establishes clinical usefulness. Scores across cohorts should not be treated as directly comparable because endpoints, prevalence, sample sizes, and source data differ.

These are internal evaluations of the supplied sampled dataset, not validated clinical or population risk estimates. The files describe cancer-patient records, not a verified survivor-only cohort. Four coursework exports have no usable stage field; only the separate Liver source has Combined Summary Stage. Area income is contextual, not personal. Treatment codes are incomplete, confounding is substantial, and no causal treatment-benefit or individualized treatment recommendation can be inferred. External validation and a prospectively defined clinical question would be necessary before clinical use.

## Privacy

This page contains only the approved cohort-level values above. No raw SEER extract, identifiers, patient-level row, individual prediction, local runtime file, or subgroup breakdown is published here. Source files and patient-level analysis remain local under the dataset's access requirements.
