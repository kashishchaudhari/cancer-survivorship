"""Create an aggregate-only staging manifest for the Power BI workbook."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LOCAL = OUT / "local"

TABLES = [
    ("Raw ZIP full-cohort cube", "raw_zip_full_eda_cube.csv"),
    ("Raw ZIP full-cohort margins", "raw_zip_full_eda_margins.csv"),
    ("Raw ZIP cohort counts", "raw_zip_full_eda_cohort_counts.csv"),
    ("Raw ZIP cohort summary", "raw_zip_full_eda_summary.json"),
    ("Raw ZIP model comparison", "raw_zip_model_comparison.csv"),
    ("Raw ZIP model intervals", "raw_zip_model_confidence_intervals.csv"),
    ("Raw ZIP paired differences", "raw_zip_paired_differences.csv"),
    # Survival outputs below come from the earlier outcome-stratified
    # CSRA workbook and must remain clearly labeled as that separate sample.
    ("CSRA KM curves", "km_curves.csv"),
    ("CSRA KM 60 months", "km_60months.csv"),
    ("CSRA competing risk curves", "competing_risk_curves.csv"),
    ("CSRA log-rank tests", "logrank_tests.csv"),
    ("CSRA survival cohort counts", "survival_cohort_counts.csv"),
    ("CSRA Cox hazard ratios", "cox_hazard_ratios.csv"),
    ("Model metrics", "model_comparison.csv"),
    ("CV comparison", "cv_comparison.csv"),
    ("Descriptive summary", "descriptive_summary.csv"),
    ("Subgroup performance", "subgroup_performance.csv"),
    ("Feature importance", "permutation_importance.csv"),
    ("ROC and PR curves", "model_curves.csv"),
    ("Calibration", "calibration.csv"),
    ("KM at 60 months", "km_60months.csv"),
    ("KM curves", "km_curves.csv"),
    ("Cox hazard ratios", "cox_hazard_ratios.csv"),
    ("Competing risk", "competing_risk_curves.csv"),
]


def native(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def main():
    tables = []
    for name, filename in TABLES:
        if filename.endswith(".json"):
            summary = json.loads((OUT / filename).read_text(encoding="utf-8"))
            frame = pd.DataFrame([
                {"metric": key, "value": json.dumps(value) if isinstance(value, (dict, list)) else value}
                for key, value in summary.items()
            ])
        else:
            frame = pd.read_csv(OUT / filename)
        tables.append({
            "name": name,
            "columns": list(frame.columns),
            "rows": [[native(value) for value in row] for row in frame.itertuples(index=False, name=None)],
        })
    manifest = {
        "title": "Cancer survivor suicide outcome analysis dashboard data",
        "scope": "Full-cohort exploratory aggregates across five raw extracts, plus separate internal model evaluation tables",
        "warning": "All uploaded tables are aggregate counts/statistics; no patient-level rows or identifiers are included. Outcome data are unavailable for some records and must not be interpreted as no event. Model metrics are exploratory, not clinically validated or population-risk estimates.",
        "tables": tables,
    }
    LOCAL.mkdir(parents=True, exist_ok=True)
    path = LOCAL / "powerbi_tables.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    print(f"Wrote {len(tables)} aggregate tables to {path}")


if __name__ == "__main__":
    main()
