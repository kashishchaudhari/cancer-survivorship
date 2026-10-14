# KPI observatory: design and metric definitions

The opening view is designed around the project's central research constraint: outcomes are only interpretable when the study population and coverage are visible. The layout pairs large-number KPIs with an interactive cohort coverage diagram and a separate care study.

## Visual direction

An editorial research brief uses a warm paper background, dark teal primary metric, serif display headline, restrained amber for missing coverage, and numbered metric panels. The coverage constellation plots actual cohort coverage on the horizontal axis, with cohort categories vertically and bubble sizes conveying relative patient volume. Selecting a cohort highlights its point and updates all four main KPIs.

The missing-outcome strip displays the recorded/unavailable split of the selected cohort. A separate care-study ribbon gives management-timing and follow-up coverage in the selected care cohort and links to its detailed analysis. The evidence rail identifies schema checks, exploratory prediction and unestablished treatment benefit as distinct layers.

## KPI definitions

| Metric | Numerator | Denominator / scope |
| --- | --- | --- |
| Unique index patients | Sum of selected aggregate patient counts | One earliest included diagnosis per linked person in the selected descriptive cohort |
| Recorded outcome coverage | Selected patients with a usable linked outcome | All selected index patients |
| Outcome unavailable | Selected total minus selected known outcomes | Displayed as a count; never assigned a negative label |
| Recorded suicide outcomes | Explicit recorded suicide outcomes | Count with secondary fraction among selected known outcomes; variable follow-up |
| Care management-timing coverage | Patients with interpretable recorded timing | Full selected care cohort; independent of the main cohort selector |
| Care follow-up coverage | Patients with usable all-cause follow-up | Full selected care cohort; independent of the main cohort selector |

Recorded event fraction is not an annual, fixed-horizon or personal clinical risk estimate. Coverage percentages describe data availability. The amber cue below 50% coverage is a visual description, not a clinical decision threshold.

## Interaction and accessibility

The cohort dropdown supports keyboard selection. Each metric has an expandable explanation. The coverage strip has a text alternative. The desktop layout uses four metric columns; narrow layouts use two, with stacked analysis panels. Reduced-motion preferences disable the entry animation. The care-study link retains the separate analysis population.

## Confidentiality

Metric values load from validated local aggregate tables. Confidential values and screenshots remain local. The same interface runs against explicitly invented fixtures in GitHub CI. Public source code contains metric definitions and styling; real-data hosting and uploads remain disabled.
