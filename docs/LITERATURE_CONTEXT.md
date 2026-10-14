# Literature context and model-evaluation comparison

This review checks whether the project's design and claims line up with established prediction-model reporting, appraisal, and cancer-registry guidance. It is not a systematic review and it is not a performance benchmark. The source data are confidential, and the project endpoint is historical treatment coding or all-cause survival—not the same endpoint, population, or use case as published clinical models.

## What aligns with current guidance

| Published guidance | What it asks researchers to make clear | Project alignment |
| --- | --- | --- |
| TRIPOD+AI (Collins et al., 2024) | Report the population, outcome, predictors, development and evaluation methods, performance, and intended use for regression or machine-learning prediction models. | The repo documents separate cohorts, endpoints, predictors, patient partitions and temporal sensitivity, baseline comparisons, calibration, and intended-use limits. The dashboard keeps study-specific results and denominator labels together. |
| PROBAST+AI (Moons et al., 2025) | Appraise participants, predictors, outcomes, analysis, and model evaluation for risk of bias and applicability. | Cohorts and coding rules are described, known treatment-code denominators are explicit, and the public docs disclose missing stage, incomplete treatment capture, and the absence of external validation. This is a self-review against domains, not a formal low-risk rating. |
| Riley et al. (2024), external validation | Evaluate a fixed model in an appropriate new dataset and assess discrimination, calibration, and clinical usefulness. | A stratified patient holdout evaluates within-source generalization after development-only cross-validation. A separate later-year sensitivity analysis tests temporal transport. Both are internal evaluations, and clinical usefulness is not demonstrated. |
| SEER treatment-data limitations | Treat RT/chemotherapy and timing fields as incomplete; distinguish “no/unknown” from confirmed no treatment; account for treatment-selection bias and unmeasured factors. | The dashboard labels recorded categories, does not equate no/unknown with no treatment, and avoids treatment-benefit claims. The surgery model predicts source coding only. |

## What is and is not comparable

Published papers often report discrimination such as AUC, but a matching metric name does not make results comparable. A fair performance comparison would require compatible cancer definitions, eligibility rules, outcome definitions, prediction time, follow-up, feature availability, missing-data handling, and validation population. This project has none of those shared benchmark conditions with the general clinical-model literature. For that reason, no published AUC is presented beside the confidential project metrics.

The project's surgery target asks whether a known source code recorded primary-site surgery. That is a documentation/assignment-pattern target, not treatment response, guideline adherence, survival benefit, or the optimal treatment. Its survival model targets all-cause survival and uses only fields available in the supplied extracts. A high score on either target would not prove clinical utility or justify a care decision.

## Gaps to close before making stronger claims

- **External validation:** evaluate a locked model on an independent, appropriately governed cohort with compatible variables and outcomes.
- **Clinical utility:** specify a real decision point and compare net benefit or another decision-relevant measure against realistic alternatives; do not infer utility from AUC alone.
- **Fairness and precision:** report uncertainty intervals and subgroup sample/event counts, then assess calibration and error patterns for adequately sized groups.
- **Predictor timing:** verify every predictor is available at the intended prediction time and exclude post-decision or post-treatment information.
- **Causal treatment effects:** define a target trial or another defensible causal design, specify eligibility and time zero, and address confounding by indication and time-dependent treatment. The current files do not support a claim about the best treatment.
- **Data permission and provenance:** confirm export filters, registry release, source terms, and written permission for each data-derived disclosure. Public display suppression alone does not grant redistribution rights.

## References

1. Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*. 2024;385:e078378. [doi:10.1136/bmj-2023-078378](https://doi.org/10.1136/bmj-2023-078378).
2. Moons KGM, Damen JAA, Kaul T, et al. PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods. *BMJ*. 2025;388:e082505. [doi:10.1136/bmj-2024-082505](https://doi.org/10.1136/bmj-2024-082505).
3. Riley RD, Archer L, Snell KIE, et al. Evaluation of clinical prediction models (part 2): how to undertake an external validation study. *BMJ*. 2024;384:e074820. [doi:10.1136/bmj-2023-074820](https://doi.org/10.1136/bmj-2023-074820).
4. Noone AM, Lund JL, Mariotto A, et al. Comparison of SEER Treatment Data With Medicare Claims. *Medical Care*. 2016;54(9):e55–e64. [doi:10.1097/MLR.0000000000000073](https://doi.org/10.1097/MLR.0000000000000073).
5. National Cancer Institute, SEER. [Acknowledgment of Treatment Data Limitations (November 2025 submission)](https://seer.cancer.gov/data-software/documentation/seerstat/nov2025/treatment-limitations-nov2025.html).
6. Giordano SH, Kuo YF, Duan Z, et al. Limits of observational data in determining outcomes from cancer therapy. *Cancer*. 2008;112(11):2456–2466. [doi:10.1002/cncr.23452](https://doi.org/10.1002/cncr.23452).

This comparison is informed by the cited reporting and methods sources. The assessment of this repository's alignment is the project author's interpretation, not an endorsement or certification from the guideline authors.
