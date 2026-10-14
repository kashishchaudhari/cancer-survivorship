"""Generate invented software-test fixtures; never read confidential sources."""
import argparse
import csv
import json
from pathlib import Path

from build_dashboard_static import CONTRACTS
from build_care_equity import FIELDS


def generate(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    tables = {
        "raw_zip_full_eda_cube.csv": [
            ["Brain","40-64","Female","Unknown","2000","No suicide recorded",120],
            ["Brain","65+","Male","Unknown","2000","Suicide outcome recorded",12],
            ["Liver","65+","Male","Unknown","2000","No suicide recorded",80],
            ["Liver","40-64","Female","Unknown","2000","Outcome unavailable",35]],
        "raw_zip_model_comparison.csv": [["Logistic regression","Synthetic baseline",.65,.10,.10,.05,.05,2,1], ["XGBoost","Synthetic baseline",.7,.12,.12,.05,.05,2.4,2]],
        "km_curves.csv": [["cancer_site","Brain",0,1,1,1],["cancer_site","Brain",60,.9,.8,.95],["sex","Male",60,.9,.8,.95]],
        "km_60months.csv": [["cancer_site","Brain",60,.9,.8,.95,20],["sex","Male",60,.9,.8,.95,20]],
        "competing_risk_curves.csv": [["cancer_site","Brain",0,0],["cancer_site","Brain",60,.02],["sex","Male",60,.02]],
        "logrank_tests.csv": [["cancer_site",2,1,.15],["sex",2,1,.15]],
        "care_timing_cube.csv": [["Liver","65+","Area median ≥ $75k","Localized","1–30 days",24,"Reported"], ["Liver","40-64","Area median < $50k","Distant","31–60 days",12,"Reported"], ["Liver","65+","Area median ≥ $75k","Regional","Unknown / unavailable",13,"Reported"], ["Liver","Under 40","Unknown area income","Unknown / unavailable","Unknown / unavailable","","Suppressed"]],
        "care_field_audit.csv": [[cohort,field,source,int(field!="stage" or cohort=="Liver"),52,0 if field=="stage" and cohort=="Brain" else 40,0 if field=="stage" and cohort=="Brain" else 40/52] for cohort in ["Brain","Liver"] for field,source in FIELDS.items()],
        "care_survival.csv": [["Liver",dimension,category,months,.8,.7,.9,12] for dimension,categories in {"stage_group":["Localized","Distant","Regional"],"age_band":["65+","40-64"],"income_band":["Area median ≥ $75k","Area median < $50k"]}.items() for category in categories for months in [12,36,60]],
    }
    for name, rows in tables.items():
        with (target / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(CONTRACTS[name].split(","))
            writer.writerows(rows)
    summary = {"cohort":"Liver","diagnosis_year_start":2004,"diagnosis_year_end":2022,"index_patients":52,"timing_known_patients":36,"followup_usable_patients":50,"suppressed_cells":1,"displayable_patients":49,"min_cell_count":11,"source_rows":{"Brain":52,"Liver":52},"index_rule":"Invented fixture, no patient source", "selection_rule":"Synthetic software fixture; not a research selection result", "scope":"SYNTHETIC TEST DATA — invented values, no clinical meaning", "timing_definition":"Invented test categories", "income_definition":"Invented area-income labels", "survival_definition":"Invented test estimates, not fitted patient outcomes"}
    (target / "care_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (target / "SYNTHETIC_DATA.json").write_text('{"synthetic": true, "origin": "invented software fixtures"}\n', encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".runtime/demo-data"))
    generate(parser.parse_args().output)
    print("Generated invented test fixtures; no confidential files were read.")
