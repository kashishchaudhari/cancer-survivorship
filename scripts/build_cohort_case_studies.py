"""Build whole-cohort case studies from local evaluation summaries, never patient rows."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from patient_studies import ARCHIVES


def build(studies, uncertainty, output):
    prepared = []
    for cohort in ARCHIVES:
        study = json.loads((studies / f"{cohort.lower()}.json").read_text(encoding="utf-8"))
        interval = json.loads((uncertainty / f"{cohort.lower()}-uncertainty.json").read_text(encoding="utf-8"))
        if study["synthetic"] or study["cohort"] != cohort:
            raise ValueError("Case studies require matching real-data aggregate evaluations")
        assignment = study["treatment_assignment"]
        if assignment.get("strategy") != "patient" or interval.get("cohort", cohort) != cohort:
            raise ValueError("Evaluation and uncertainty cohorts disagree")
        prepared.append((cohort, study, interval))
    output.mkdir(parents=True, exist_ok=True)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none", "svg.hashsalt": "cohort-baselines"})
    index = ["# Five independent cancer case studies", "",
             "Each study preserves its own source, index patients, known-code denominator, and evaluation. "
             "The primary design uses a stratified patient holdout with development-only cross-validation; "
             "temporal evaluation is a secondary sensitivity analysis.", "",
             "| Study | Patient-test n | ROC AUC (95% fixed-model interval) | Average precision | Test prevalence baseline |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for cohort, study, interval in prepared:
        assignment = study["treatment_assignment"]
        primary, temporal = assignment["test"], assignment["temporal_sensitivity"]["test"]
        low, high = interval["auc_ci"]
        filename = f"{cohort.upper()}_STUDY.md"
        index.append(f"| [{cohort}]({filename}) | {primary['patients']:,} | {primary['roc_auc']:.3f} ({low:.3f}–{high:.3f}) | {primary['average_precision']:.3f} | {primary['prevalence']:.3f} |")
        if cohort == "Liver" and (output / filename).exists() and (assets / "liver-evaluation.svg").exists():
            continue
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
        fig.patch.set_facecolor("#f8faf6")
        panels = [([primary["prevalence"], primary["average_precision"]],
                   ["Test prevalence", "Model"], "Average precision · higher is better"),
                  ([interval["constant_baseline_brier"], primary["brier"]],
                   ["Development baseline", "Model"], "Brier score · lower is better")]
        for ax, (values, labels, title) in zip(axes, panels):
            ax.set_facecolor("#f8faf6")
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", alpha=.15)
            ax.set_axisbelow(True)
            upper = min(1.12, max(values) * 1.22)
            ax.set_ylim(0, upper)
            ax.set_title(title, fontsize=12, pad=14)
            for bar, value in zip(ax.bar(labels, values, color=["#a2afa5", "#147d70"], width=.55), values):
                ax.text(bar.get_x() + bar.get_width()/2, value + upper*.03, f"{value:.3f}", ha="center", fontweight="bold")
        fig.suptitle(f"{cohort} · recorded surgery prediction", x=.07, ha="left", fontsize=17, fontweight="bold")
        fig.text(.07, .86, f"Stratified patient holdout · {primary['patients']:,} test patients · internal sampled-dataset evaluation", fontsize=10, color="#465b50")
        fig.text(.07, .03, "Known surgery codes only. These scores do not estimate treatment benefit or clinical risk.", fontsize=9, color="#465b50")
        fig.subplots_adjust(top=.72, bottom=.19, left=.08, right=.98, wspace=.28)
        figure = assets / f"{cohort.lower()}-evaluation.svg"
        fig.savefig(figure, metadata={"Date": None})
        plt.close(fig)
        figure.write_text("\n".join(line.rstrip() for line in figure.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
        # Preserve the already published, more detailed Liver narrative.
        if cohort == "Liver" and (output / filename).exists():
            continue
        source = study["source"]
        survival = study["model"]
        stage = "Source summary stage is available and used." if "stage" in assignment["features"] else "This coursework source has no usable stage field. Stage is excluded; grade is not a stage proxy."
        report = [f"# {cohort} cancer: care patterns and held-out evaluation", "",
                  f"The supplied source contains {source['source_rows']:,} records and {source['index_patients']:,} earliest-index patients. {stage}", "",
                  "## Recorded-surgery model", "",
                  "The model predicts whether primary-site surgery is recorded among known codes: 00 versus 01–90. Unknown/other codes are excluded. Inputs: " + ", ".join(assignment["features"]) + ".", "",
                  "| Measure | Patient holdout | Temporal sensitivity |", "| --- | ---: | ---: |",
                  f"| Test patients | {primary['patients']:,} | {temporal['patients']:,} |",
                  f"| Surgery recorded in test | {primary['positive']:,} | {temporal['positive']:,} |",
                  f"| Test prevalence / random-ranking AP baseline | {primary['prevalence']:.3f} | {temporal['prevalence']:.3f} |",
                  f"| Average precision | {primary['average_precision']:.3f} | {temporal['average_precision']:.3f} |",
                  f"| ROC AUC | {primary['roc_auc']:.3f} | {temporal['roc_auc']:.3f} |",
                  f"| Brier score (lower is better) | {primary['brier']:.3f} | {temporal['brier']:.3f} |", "",
                  f"Primary ROC AUC has a 95% percentile bootstrap interval of **{low:.3f}–{high:.3f}** from {interval['bootstrap_replicates']:,} fixed-model test-patient resamples (seed {interval['seed']}). This excludes training and model-selection uncertainty. Average precision is {primary['average_precision']/primary['prevalence']:.2f} times its own test prevalence baseline. The constant-probability baseline, fixed at development prevalence, has Brier {interval['constant_baseline_brier']:.3f}.", "",
                  f"![{cohort} recorded-surgery prediction versus simple baselines](assets/{cohort.lower()}-evaluation.svg)", "",
                  f"Development contains {assignment['splits']['development']['patients']:,} eligible patients. Five development-only folds select regularization, with preprocessing fitted within each training fold; the final model fits development only. The primary 80/20 patient split is reproducible (seed 20261014). Eligibility remains 2010–2017 for the existing legacy-grade source era; years no longer assign the primary partitions.", "",
                  "The temporal sensitivity uses different, overlapping source populations. Score differences do not establish improvement caused by a split change. High average precision can partly reflect high surgery prevalence; it must be compared with the baseline. Cross-cancer scores are not a fair ranking of clinical performance.", "",
                  "## Separate all-cause survival model", "",
                  f"The penalized Cox model has test C-index **{survival['evaluation']['c_index']:.3f}** on {survival['splits']['test']['patients']:,} patients. Its separate patient split is stratified by death status; development folds select regularization by concordance.", "",
                  "| Horizon | Cox IPCW Brier | Development KM baseline | Test patients at risk |", "| --- | ---: | ---: | ---: |"]
        for metric in survival["evaluation"]["metrics"]:
            score = "Unsupported" if metric["ipcw_brier"] is None else f"{metric['ipcw_brier']:.3f}"
            baseline = "Unsupported" if metric["baseline_brier"] is None else f"{metric['baseline_brier']:.3f}"
            report.append(f"| {metric['months']/12:g} year | {score} | {baseline} | {metric['at_risk']:,} |")
        report += ["", "## Interpretation and reproducibility", "",
                   "These are **revised internal evaluations of the supplied sampled dataset**, not validated clinical or population risk estimates. Earlier findings were inspected; this resplit is not independent confirmatory validation. Treatment codes are incomplete, predictor availability at a clinical decision time is unverified, area income is contextual, and confounding and informative censoring remain. No treatment-benefit or individualized recommendation is established.", "",
                   "The public dashboards use invented values only. This report contains whole-cohort aggregates; raw records, predictions, trained models, and subgroup results stay local.", "",
                   f"See the [study design](TREATMENT_MODEL.md), [all five case studies](CASE_STUDIES.md), and [original dashboard](https://kashishchaudhari.github.io/cancer-survivorship/observatory/).", "",
                   "```powershell", f'uv run python scripts/evaluate_cohort_uncertainty.py --cohort {cohort} --folder "C:\\approved\\Datasets" --studies .runtime/patient-studies --output .runtime/{cohort.lower()}-uncertainty.json', "```", ""]
        (output / filename).write_text("\n".join(report), encoding="utf-8")
    index += ["", "Intervals describe fixed-model test-sample uncertainty only. Compare average precision with each cohort's prevalence; these are internal evaluations, not clinical or population estimates.", "",
              "Both dashboard layouts are retained: the [five-cancer Patient Atlas](https://kashishchaudhari.github.io/cancer-survivorship/) and the [original observatory](https://kashishchaudhari.github.io/cancer-survivorship/observatory/). Their endpoints and source populations remain distinct.", ""]
    (output / "CASE_STUDIES.md").write_text("\n".join(index), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studies", type=Path, required=True)
    parser.add_argument("--uncertainty", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".runtime/cohort-reports"))
    args = parser.parse_args()
    build(args.studies, args.uncertainty, args.output)
