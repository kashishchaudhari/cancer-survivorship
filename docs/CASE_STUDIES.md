# Five independent cancer case studies

Each study preserves its own source, index patients, known-code denominator, and evaluation. The primary design uses a stratified patient holdout with development-only cross-validation; temporal evaluation is a secondary sensitivity analysis.

| Study | Patient-test n | ROC AUC (95% fixed-model interval) | Average precision | Test prevalence baseline |
| --- | ---: | ---: | ---: | ---: |
| [Brain](BRAIN_STUDY.md) | 2,636 | 0.609 (0.583–0.633) | 0.786 | 0.736 |
| [Breast](BREAST_STUDY.md) | 28,515 | 0.716 (0.704–0.728) | 0.951 | 0.908 |
| [Prostate](PROSTATE_STUDY.md) | 25,156 | 0.695 (0.688–0.701) | 0.544 | 0.368 |
| [Skin](SKIN_STUDY.md) | 11,304 | 0.568 (0.549–0.589) | 0.942 | 0.929 |
| [Liver](LIVER_STUDY.md) | 4,074 | 0.823 (0.809–0.836) | 0.601 | 0.236 |

Intervals describe fixed-model test-sample uncertainty only. Compare average precision with each cohort's prevalence; these are internal evaluations, not clinical or population estimates.

Both dashboard layouts are retained: the [five-cancer Patient Atlas](https://kashishchaudhari.github.io/cancer-survivorship/) and the [original observatory](https://kashishchaudhari.github.io/cancer-survivorship/observatory/). Their endpoints and source populations remain distinct.
