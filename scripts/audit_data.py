"""Audit and prepare the supplied workbook without altering its source."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/local/CSRA.xlsx"
OUT = ROOT / "outputs"
LOCAL = OUT / "local"
RENAME = {
    "Age recode with <1 year olds": "age_raw",
    "Race recode (W, B, AI, API)": "race",
    "Sex": "sex",
    "Site recode ICD-O-3/WHO 2008": "cancer_site",
    "Year of diagnosis": "diagnosis_year",
    "COD to site recode": "cod",
    "Survival months": "survival_months",
    "Vital status recode (study cutoff used)": "vital_status",
    "Event": "event",
    "Censoring_Type": "censoring_type",
}
FEATURES = ["age_cat", "sex", "race", "cancer_site"]


def age_category(label):
    label = str(label).strip().removesuffix(" years")
    if not re.fullmatch(r"\d{2}(?:-\d{2}|\+)?", label):
        return None
    age = int(label[:2])
    return "Young" if age < 40 else "Middle-aged" if age < 65 else "Older"


def prepare(raw):
    if set(RENAME) - set(raw.columns):
        raise ValueError(f"Missing required columns: {set(RENAME) - set(raw.columns)}")
    d = raw.rename(columns=RENAME).copy()
    d.insert(0, "row_id", np.arange(1, len(d) + 1))
    # Group all exact source-row duplicates together in every ML partition.
    d["duplicate_group"] = pd.util.hash_pandas_object(raw.fillna("<NA>"), index=False).astype(str)
    for col in ["age_raw", "race", "sex", "cancer_site", "cod", "vital_status", "censoring_type"]:
        d[col] = d[col].astype("string").str.strip()
    d["age_cat"] = d.age_raw.map(age_category)
    d["cancer_site"] = d.cancer_site.replace({"Intrahepatic Bile Duct": "Liver"})
    d["event"] = pd.to_numeric(d.event, errors="coerce")
    d["survival_months"] = pd.to_numeric(d.survival_months, errors="coerce")
    d.loc[d.survival_months.eq(9999), "survival_months"] = np.nan
    event_from_cod = d.cod.eq("Suicide and Self-Inflicted Injury")
    if not d.event.isin([0, 1]).all() or not d.event.eq(event_from_cod.astype(int)).all():
        raise ValueError("Event is invalid or disagrees with cause of death")
    status_from_type = d.censoring_type.map({"Suicide": 1, "Other_Death": 2, "Alive": 0})
    if status_from_type.isna().any() or not d.event.eq(status_from_type.eq(1).astype(int)).all():
        raise ValueError("Event disagrees with censoring category")
    if not d.vital_status.eq(d.censoring_type.map({"Suicide": "Dead", "Other_Death": "Dead", "Alive": "Alive"})).all():
        raise ValueError("Vital status disagrees with censoring category")
    d["status"] = status_from_type.astype(int)
    # Retain Unknown race as an explicit category; do not manufacture an age.
    valid = d.age_cat.notna() & d[FEATURES].notna().all(axis=1)
    d["ml_eligible"] = valid
    d["survival_eligible"] = valid & d.survival_months.notna() & d.survival_months.ge(0)
    # Zero months are interval-rounded values, not absent follow-up.
    d["analysis_time"] = d.survival_months.mask(d.survival_months.eq(0), 0.5)
    return d


def main():
    OUT.mkdir(exist_ok=True)
    LOCAL.mkdir(exist_ok=True)
    raw = pd.read_excel(SOURCE, dtype={"Survival months": str})
    d = prepare(raw)
    audit = {
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_rows": len(raw),
        "source_suicide_events": int(d.event.sum()),
        "source_event_fraction": float(d.event.mean()),
        "exact_duplicate_rows_beyond_first": int(raw.duplicated().sum()),
        "unique_source_profiles": int(d.duplicate_group.nunique()),
        "zero_month_rows": int(d.survival_months.eq(0).sum()),
        "missing_or_unknown_survival_rows": int(d.survival_months.isna().sum()),
        "ml_rows": int(d.ml_eligible.sum()),
        "survival_rows": int(d.survival_eligible.sum()),
        "ml_excluded": int((~d.ml_eligible).sum()),
        "survival_excluded": int((~d.survival_eligible).sum()),
        "unknown_race_rows": int(d.race.eq("Unknown").sum()),
        "male_breast_rows": int((d.sex.eq("Male") & d.cancer_site.eq("Breast")).sum()),
        "diagnosis_year_min": int(d.diagnosis_year.min()),
        "diagnosis_year_max": int(d.diagnosis_year.max()),
        "outcome_counts": d.censoring_type.value_counts().to_dict(),
        "age_counts": d.age_cat.value_counts().to_dict(),
        "source_missing_by_column": raw.isna().sum().to_dict(),
        "policy": "Unknown race and male breast records retained; unknown survival excluded only from survival models; zero months mapped to 0.5 for survival models; exact duplicate source rows remain in the same ML partition.",
    }
    (OUT / "data_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    d.to_csv(LOCAL / "cleaned_cohort.csv", index=False)
    tables = []
    for variable in FEATURES:
        for group, g in d[d.ml_eligible].groupby(variable, observed=True):
            tables.append({"variable": variable, "group": group, "records": len(g),
                           "suicide_events": int(g.event.sum()), "event_fraction": float(g.event.mean()),
                           "percent_of_cohort": len(g) / int(d.ml_eligible.sum()),
                           "median_observed_months": g.survival_months.median()})
    pd.DataFrame(tables).to_csv(OUT / "descriptive_summary.csv", index=False)
    # Local Power BI fact table retains dimensions and event counts; no raw identifiers.
    cube = d[d.ml_eligible].groupby(FEATURES + ["diagnosis_year", "censoring_type"], observed=True).agg(
        records=("row_id", "size"), suicide_events=("event", "sum")
    ).reset_index()
    cube.to_csv(LOCAL / "cohort_cube.csv", index=False)
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
