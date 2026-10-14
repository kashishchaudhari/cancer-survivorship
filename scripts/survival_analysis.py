"""Exploratory survival analyses for the supplied outcome-sampled cohort.

Other-cause deaths are censored for Kaplan-Meier/Cox/AFT estimates and are
handled as a competing event in the Aalen-Johansen analysis. These estimates
describe this supplied sample; they are not population risk estimates.
"""
from pathlib import Path
import json
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".runtime" / "matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import AalenJohansenFitter, CoxPHFitter, KaplanMeierFitter, WeibullAFTFitter
from lifelines.statistics import multivariate_logrank_test, proportional_hazard_test

from audit_data import FEATURES, LOCAL, OUT

GROUPS = ["cancer_site", "race", "sex", "age_cat"]
REFERENCE_LEVELS = {
    "age_cat": ["Young", "Middle-aged", "Older"],
    "sex": ["Female", "Male"],
    "race": ["White", "Black", "Asian or Pacific Islander", "American Indian/Alaska Native"],
    "cancer_site": ["Brain", "Breast", "Liver", "Prostate"],
}


def at_or_before(table, month):
    eligible = table.index[table.index <= month]
    return table.loc[eligible.max()] if len(eligible) else table.iloc[0]


def design_matrix(data):
    frame = data[["analysis_time", "event", "duplicate_group", *FEATURES]].copy()
    for column, levels in REFERENCE_LEVELS.items():
        frame[column] = pd.Categorical(frame[column], categories=levels, ordered=True)
    return pd.get_dummies(frame, columns=FEATURES, drop_first=True, dtype=float)


def collapse_model_rows(matrix):
    """Use frequency weights for exact model-row duplicates."""
    columns = [column for column in matrix.columns if column != "duplicate_group"]
    return matrix.groupby(columns, dropna=False, observed=True).size().rename("frequency_weight").reset_index()


def main():
    OUT.mkdir(exist_ok=True)
    data = pd.read_csv(LOCAL / "cleaned_cohort.csv", dtype={"duplicate_group": str})
    data = data[data.survival_eligible].copy()
    data["analysis_time"] = pd.to_numeric(data.analysis_time)
    data["event"] = data.event.astype(int)
    data["status"] = data.status.astype(int)

    pd.DataFrame([
        {"cohort": "All eligible records", "records": len(data), "suicide_events": int(data.event.sum())},
        {"cohort": "Known race regression", "records": int(data.race.ne("Unknown").sum()),
         "suicide_events": int(data.loc[data.race.ne("Unknown"), "event"].sum())},
    ]).to_csv(OUT / "survival_cohort_counts.csv", index=False)

    curve_rows, survival_60, logrank_rows = [], [], []
    for variable in GROUPS:
        result = multivariate_logrank_test(data.analysis_time, data[variable], data.event)
        logrank_rows.append({"variable": variable, "test_statistic": result.test_statistic,
                             "degrees_of_freedom": result.degrees_of_freedom, "p_value": result.p_value})
        for group, subset in data.groupby(variable, observed=True):
            km = KaplanMeierFitter(label=str(group)).fit(subset.analysis_time, subset.event)
            sf = km.survival_function_.rename(columns={str(group): "survival"})
            ci = km.confidence_interval_.copy()
            ci.columns = ["ci_low", "ci_high"]
            joined = sf.join(ci).reset_index(names="months")
            joined.insert(0, "group", group)
            joined.insert(0, "variable", variable)
            curve_rows.extend(joined.to_dict("records"))
            s60 = float(km.predict(60))
            ci60 = at_or_before(ci, 60)
            risk_times = km.event_table.index[km.event_table.index <= 60]
            n_risk = int(km.event_table.loc[risk_times.max(), "at_risk"]) if len(risk_times) else len(subset)
            survival_60.append({"variable": variable, "group": group, "months": 60,
                                "survival": s60, "ci_low": float(ci60.iloc[0]),
                                "ci_high": float(ci60.iloc[1]), "n_risk": n_risk})
    pd.DataFrame(curve_rows).to_csv(OUT / "km_curves.csv", index=False)
    pd.DataFrame(survival_60).to_csv(OUT / "km_60months.csv", index=False)
    pd.DataFrame(logrank_rows).to_csv(OUT / "logrank_tests.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for ax, variable in zip(axes.flat, GROUPS):
        for group, subset in data.groupby(variable, observed=True):
            KaplanMeierFitter().fit(subset.analysis_time, subset.event, label=str(group)).plot_survival_function(
                ax=ax, ci_show=False, censor_styles={"ms": 2})
        ax.set(title=f"Suicide-free survival by {variable.replace('_', ' ')}",
               xlabel="Months after diagnosis", ylabel="Estimated survival")
        ax.set_ylim(0.88, 1.002)
        ax.legend(fontsize=7)
    fig.savefig(OUT / "km_curves.png", dpi=160)
    plt.close(fig)

    aj_rows = []
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for group, subset in data.groupby("cancer_site", observed=True):
        aj = AalenJohansenFitter(calculate_variance=False, seed=20261010).fit(
            subset.analysis_time, subset.status, event_of_interest=1, label=str(group))
        cif = aj.cumulative_density_.reset_index()
        cif.columns = ["months", "suicide_cumulative_incidence"]
        cif.insert(0, "group", group)
        cif.insert(0, "variable", "cancer_site")
        aj_rows.extend(cif.to_dict("records"))
        ax.step(cif.months, cif.suicide_cumulative_incidence, where="post", label=str(group))
    ax.set(title="Suicide cumulative incidence with other death as a competing event",
           xlabel="Months after diagnosis", ylabel="Cumulative incidence")
    ax.legend()
    fig.savefig(OUT / "competing_risk_curves.png", dpi=160)
    plt.close(fig)
    pd.DataFrame(aj_rows).to_csv(OUT / "competing_risk_curves.csv", index=False)

    regression = data[data.race.ne("Unknown")].copy()
    matrix = collapse_model_rows(design_matrix(regression))
    cox = CoxPHFitter().fit(matrix, duration_col="analysis_time", event_col="event",
                           weights_col="frequency_weight", robust=True)
    cox_table = cox.summary.reset_index(names="term")
    cox_table[["term", "exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]].rename(columns={
        "exp(coef)": "hazard_ratio", "exp(coef) lower 95%": "ci_low",
        "exp(coef) upper 95%": "ci_high", "p": "p_value",
    }).to_csv(OUT / "cox_hazard_ratios.csv", index=False)
    ph = proportional_hazard_test(cox, matrix, time_transform="rank").summary.reset_index(names="term")
    ph.rename(columns={"test_statistic": "ph_test_statistic", "p": "p_value"}).to_csv(
        OUT / "cox_ph_tests.csv", index=False)

    aft = WeibullAFTFitter().fit(matrix, duration_col="analysis_time", event_col="event",
                                weights_col="frequency_weight", robust=True)
    aft_table = aft.summary.reset_index()
    aft_table = aft_table[(aft_table.param.eq("lambda_")) & aft_table.covariate.ne("Intercept")].copy()
    aft_table["time_ratio"] = np.exp(aft_table.coef)
    aft_table["ci_low"] = np.exp(aft_table["coef lower 95%"])
    aft_table["ci_high"] = np.exp(aft_table["coef upper 95%"])
    aft_table[["covariate", "time_ratio", "ci_low", "ci_high", "p"]].rename(
        columns={"covariate": "term", "p": "p_value"}).to_csv(OUT / "aft_time_ratios.csv", index=False)

    sensitivity = []
    for label, replacement in [("0.5 months", 0.5), ("1 month", 1.0), ("exclude", None)]:
        subset = regression.copy()
        if replacement is None:
            subset = subset[subset.survival_months.gt(0)]
        else:
            subset.loc[subset.survival_months.eq(0), "analysis_time"] = replacement
        mx = collapse_model_rows(design_matrix(subset))
        fit = CoxPHFitter().fit(mx, "analysis_time", "event", weights_col="frequency_weight", robust=True)
        table = fit.summary.reset_index(names="term")
        for _, row in table.iterrows():
            sensitivity.append({"zero_month_rule": label, "records": len(subset), "term": row["term"],
                                "hazard_ratio": np.exp(row["coef"]),
                                "ci_low": np.exp(row["coef lower 95%"]),
                                "ci_high": np.exp(row["coef upper 95%"]),
                                "p_value": row["p"]})
    pd.DataFrame(sensitivity).to_csv(OUT / "zero_month_sensitivity.csv", index=False)

    summary = {
        "records": len(data), "suicide_events": int(data.event.sum()),
        "regression_records": len(regression), "reference_levels": {k: v[0] for k, v in REFERENCE_LEVELS.items()},
        "interpretation": "Exploratory internal estimates for the supplied outcome-sampled cohort; not validated clinical or population risk estimates.",
        "other_death_handling": "Censored in KM/Cox/AFT and modeled as a competing event in Aalen-Johansen estimates.",
    }
    (OUT / "survival_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
