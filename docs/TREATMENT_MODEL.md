# Treatment-pattern model and study design

## Research question

Within each supplied cancer cohort, how well can demographic and tumor descriptors predict whether primary-site surgery appears in the source record? How does recorded treatment coding vary across the groups we can observe, and how well does a separate all-cause survival model rank later-year outcomes?

This is a model of **recorded historical treatment assignment**. It does not estimate treatment effectiveness, the best treatment for a patient, or a treatment effect. The data lack the clinical condition, anatomy, comorbidity, patient preference, contraindication, and treatment-selection details needed to answer those questions.

## Independent study populations

The four `CancerProject2025` RAR text exports are Brain, Breast, Prostate, and Skin. The fifth study reads the Liver raw text extract from the supplied ZIP. The application normalizes, profiles, models, and evaluates each study separately. It does not link patients across those source systems or pool cancer types. Duplicate patient IDs within a source are reduced to the earliest diagnosis year before analysis.

The pipeline records source SHA-256 fingerprints and compares each course archive's extracted text with the corresponding raw ZIP member when the ZIP path is supplied. The Liver raw extract is compared directly with its ZIP member. These checks establish byte-level identity for the checked source file; they do not establish representativeness, registry coverage, or permission to redistribute the data.

## Available stage

Brain, Breast, Prostate, and Skin coursework extracts contain no usable stage column. Their stage filters are disabled, and stage is excluded from model inputs. The Liver raw extract contains `Combined Summary Stage (2004+)`; a stage filter and stage-specific model feature are enabled only for that study. This is the source's summary stage field, not AJCC stage. Earlier years and unavailable values remain unknown. Grade is kept separate from stage.

## Surgery-recording model

The binary target is a known primary-site surgery code: `00` is coded as no recorded surgery; codes `01` through `90` are coded as surgery recorded. Unknown and other codes are excluded, and every dashboard label names this denominator. This is not a complete account of all surgical procedures.

The model is regularized logistic regression. Inputs are source-age-band midpoint, recorded sex, grade, area-income category, source stage where available, and Breast subtype where supported. The split is by index diagnosis year: development 2010–2013, validation 2014–2015, and held-out test 2016–2017. The validation period chooses among four regularization strengths using average precision. The final model is fit on development plus validation and evaluated once on later years.

The dashboard reports test average precision beside test prevalence, ROC AUC, Brier score, and grouped calibration. Average precision is interpreted against prevalence because surgery recording is imbalanced. The API returns a probability of source-recorded surgery for a supported profile and labels it as a historical coding-pattern estimate. It never describes that probability as a treatment recommendation.

## Survival model

Each study also fits a penalized Cox model for all-cause survival at 12, 36, and 60 months. It uses the same temporal split, selects regularization on validation, compares against a development/validation Kaplan–Meier baseline, and reports IPCW Brier scores, grouped held-out calibration, and subgroup concordance. Treatment, follow-up, vital status, and diagnosis year are excluded as predictors. Zero-month records are represented at 0.5 months only for the Cox fit; descriptive survival retains the recorded time.

This remains internal temporal evaluation of supplied historical data. It is not external validation. Population shift, treatment-selection bias, incomplete covariates, non-proportional hazards, and source extraction rules may change performance. Subgroup metrics have sample and event-count constraints. The dashboard labels its estimate as a research-model output, not a clinical prognosis.

## What a stronger treatment-benefit study needs

A defensible comparative-effectiveness analysis needs a specified clinical decision point, eligible treatment alternatives, stage and tumor characteristics before treatment, comorbidities, performance status, treatment start dates and combinations, longitudinal outcomes, censoring rules, and a prespecified causal design. At a minimum, it also requires sensitivity analysis for measured and unmeasured confounding. The current coursework exports do not meet that bar, so this project stops at treatment patterns and recorded-assignment prediction.

## Reproducibility and privacy

Run `scripts/patient_studies.py` locally, then package with `scripts/build_patient_site.py`. Patient identifiers are used only in local memory for within-source deduplication. Model files, aggregate study JSON, derived results, and predictions are ignored under `.runtime/`. CI runs invented fixtures and code checks; it does not access the source archives or publish build artifacts.
