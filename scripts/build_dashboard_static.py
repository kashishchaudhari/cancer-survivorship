"""Validate aggregate data and package an allowlisted dashboard release."""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "raw_zip_full_eda_cube.csv": ROOT / "outputs/raw_zip_full_eda_cube.csv",
    "raw_zip_model_comparison.csv": ROOT / "outputs/raw_zip_model_comparison.csv",
    "km_curves.csv": ROOT / "outputs/km_curves.csv",
    "competing_risk_curves.csv": ROOT / "outputs/competing_risk_curves.csv",
    "km_60months.csv": ROOT / "outputs/km_60months.csv",
    "logrank_tests.csv": ROOT / "outputs/logrank_tests.csv",
}
CONTRACTS = {
    "raw_zip_full_eda_cube.csv": "source_cohort,age_band,sex,race,diagnosis_decade,outcome_state,patient_count",
    "raw_zip_model_comparison.csv": "model,feature_set,roc_auc,average_precision,sample_average_precision,sample_test_prevalence,weighted_test_prevalence,average_precision_lift_over_weighted_prevalence,fit_seconds",
    "km_curves.csv": "variable,group,months,survival,ci_low,ci_high",
    "competing_risk_curves.csv": "variable,group,months,suicide_cumulative_incidence",
    "km_60months.csv": "variable,group,months,survival,ci_low,ci_high,n_risk",
    "logrank_tests.csv": "variable,test_statistic,degrees_of_freedom,p_value",
    "care_field_audit.csv": "cohort,field,source_field,present,eligible_patients,usable_patients,usable_fraction",
    "care_timing_cube.csv": "cohort,age_band,income_band,stage_group,timing_band,patient_count,status",
    "care_survival.csv": "cohort,dimension,category,months,survival,ci_low,ci_high,n_risk",
}
TEXT_FIELDS = {"source_cohort", "age_band", "sex", "race", "diagnosis_decade", "outcome_state", "model", "feature_set", "variable", "group", "cohort", "field", "source_field", "income_band", "stage_group", "timing_band", "status", "dimension", "category"}
PROBABILITIES = {"roc_auc", "average_precision", "sample_average_precision", "sample_test_prevalence", "weighted_test_prevalence", "survival", "ci_low", "ci_high", "suicide_cumulative_incidence", "p_value", "usable_fraction", "present"}
STATES = {"No suicide recorded", "Suicide outcome recorded", "Outcome unavailable"}


def validate_table(path: Path) -> list[dict]:
    header = CONTRACTS[path.name].split(",")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != header:
            raise ValueError(f"{path.name}: exact aggregate schema required; unexpected columns rejected")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: empty table")
    keys = set()
    for index, row in enumerate(rows, 2):
        suppressed = path.name == "care_timing_cube.csv" and row.get("status") == "Suppressed"
        if None in row or any(value is None or (not value.strip() and not (suppressed and field == "patient_count")) for field, value in row.items()):
            raise ValueError(f"{path.name}:{index}: blank or malformed field")
        values = {}
        for field in set(header) - TEXT_FIELDS:
            if suppressed and field == "patient_count":
                if row[field] != "":
                    raise ValueError("Suppressed counts must be withheld, not exported")
                continue
            try:
                value = float(row[field])
            except ValueError as exc:
                raise ValueError(f"{path.name}:{index}: invalid {field}") from exc
            if not math.isfinite(value) or value < 0 or (field in PROBABILITIES and value > 1):
                raise ValueError(f"{path.name}:{index}: out-of-range {field}")
            if field in {"patient_count", "n_risk", "degrees_of_freedom", "present", "eligible_patients", "usable_patients"} and not value.is_integer():
                raise ValueError(f"{path.name}:{index}: {field} must be an integer")
            values[field] = value
        if "ci_low" in values and not values["ci_low"] <= values["survival"] <= values["ci_high"]:
            raise ValueError(f"{path.name}:{index}: confidence interval does not contain estimate")
        if "outcome_state" in row and row["outcome_state"] not in STATES:
            raise ValueError(f"{path.name}:{index}: unrecognized outcome state")
        if path.name == "care_timing_cube.csv":
            if row["status"] not in {"Suppressed", "Reported"} or (not suppressed and values["patient_count"] < 11):
                raise ValueError("Care cells must be reported at >=11 patients or suppressed")
            key = tuple(row[field] for field in ["cohort", "age_band", "income_band", "stage_group", "timing_band"])
        elif path.name == "care_field_audit.csv":
            if values["usable_patients"] > values["eligible_patients"]:
                raise ValueError("Usable count exceeds audit denominator")
            expected = values["usable_patients"] / values["eligible_patients"] if values["eligible_patients"] else 0
            if not math.isclose(values["usable_fraction"], expected, abs_tol=1e-10):
                raise ValueError("Audit coverage does not reconcile")
            key = (row["cohort"], row["field"])
        elif path.name == "care_survival.csv":
            if values["n_risk"] < 11:
                raise ValueError("Care survival requires >=11 at risk")
            key = (row["cohort"], row["dimension"], row["category"], values["months"])
        elif path.name == "raw_zip_full_eda_cube.csv":
            key = tuple(row[field] for field in header[:-1])
        elif "months" in row:
            key = (row["variable"], row["group"], float(row["months"]))
        elif "model" in row:
            key = (row["model"], row["feature_set"])
        else:
            key = (row["variable"],)
        if key in keys:
            raise ValueError(f"{path.name}:{index}: duplicate aggregate key")
        keys.add(key)
    return rows


def build(source: Path, target: Path, revision: str = "local", synthetic: bool = False) -> dict:
    if os.environ.get("GITHUB_ACTIONS") == "true" and not synthetic:
        raise ValueError("Hosted CI must use synthetic fixtures; confidential builds stay local")
    marker = source / "SYNTHETIC_DATA.json"
    if synthetic and (not marker.exists() or json.loads(marker.read_text()).get("synthetic") is not True):
        raise ValueError("Synthetic build requires invented-fixture provenance marker")
    if marker.exists() and not synthetic:
        raise ValueError("Synthetic fixtures must be explicitly labeled with --synthetic")
    if source.resolve() == (target / "data").resolve():
        raise ValueError("Source and release data directory must be distinct")
    allowed = {"index.html", "engineering.js", "care.js", "data/manifest.json", "data/care_summary.json"} | {f"data/{name}" for name in CONTRACTS}
    if target.exists():
        unexpected = [path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file() and path.relative_to(target).as_posix() not in allowed]
        if unexpected:
            raise ValueError(f"Release directory contains non-allowlisted files: {unexpected}; use a clean target")
    # Fail before modifying the previous release if any contract is broken.
    tables = {name: validate_table(source / name) for name in CONTRACTS}
    care = json.loads((source / "care_summary.json").read_text(encoding="utf-8"))
    care_keys = {"cohort", "diagnosis_year_start", "diagnosis_year_end", "index_patients", "timing_known_patients", "followup_usable_patients", "suppressed_cells", "displayable_patients", "min_cell_count", "index_rule", "selection_rule", "scope", "timing_definition", "income_definition", "survival_definition", "source_rows"}
    if set(care) != care_keys:
        raise ValueError("Unexpected care summary fields")
    care_cube = tables["care_timing_cube.csv"]
    if sum(int(row["patient_count"]) for row in care_cube if row["status"] == "Reported") != care["displayable_patients"]:
        raise ValueError("Care summary does not reconcile with released counts")
    if sum(row["status"] == "Suppressed" for row in care_cube) != care["suppressed_cells"]:
        raise ValueError("Care suppression count does not reconcile")
    if not 0 <= care["displayable_patients"] <= care["index_patients"] or not 0 <= care["timing_known_patients"] <= care["index_patients"]:
        raise ValueError("Invalid care cohort denominator")
    if any(row["cohort"] != care["cohort"] for row in care_cube + tables["care_survival.csv"]):
        raise ValueError("Care tables mix cohorts")
    cube = tables["raw_zip_full_eda_cube.csv"]
    total = sum(int(row["patient_count"]) for row in cube)
    unavailable = sum(int(row["patient_count"]) for row in cube if row["outcome_state"] == "Outcome unavailable")
    events = sum(int(row["patient_count"]) for row in cube if row["outcome_state"] == "Suicide outcome recorded")
    manifest = {
        "schema_version": 1, "built_at_utc": datetime.now(timezone.utc).isoformat(), "synthetic": synthetic,
        "confidentiality": "SYNTHETIC TEST DATA — no clinical meaning" if synthetic else "CONFIDENTIAL — local research only; publication requires permission",
        "revision": revision, "status": "passed",
        "scope": "Internal evaluation of supplied data; not validated clinical or population risk estimates.",
        "source_refresh": "Local raw-data ETL followed by aggregate refresh; CI does not ingest patient data.",
        "cohort": {"index_patients": total, "known_outcomes": total - unavailable, "unavailable_outcomes": unavailable, "recorded_suicide_outcomes": events},
        "checks": ["Exact aggregate schemas", "Nonempty tables and required fields", "Finite numeric values and probability bounds", "Integer counts", "Unique aggregate keys", "Confidence interval consistency", "Explicit missing-outcome states", "Care count suppression and at-risk minimums", "Care audit and summary denominators reconcile"],
        "tables": [{"name": name, "rows": len(rows), "sha256": hashlib.sha256((source / name).read_bytes()).hexdigest(), "population": "Five-extract 2004–2022 field audit" if name == "care_field_audit.csv" else f"{care['cohort']} earliest-index cohort, 2004–2022" if name.startswith("care_") else "Raw-extract index cohort" if name == "raw_zip_full_eda_cube.csv" else "Raw-extract model test cohort" if "model" in name else "Earlier outcome-stratified workbook sample"} for name, rows in tables.items()],
        "care_summary": {"sha256": hashlib.sha256((source / "care_summary.json").read_bytes()).hexdigest(), "cohort": care["cohort"]},
    }
    target.mkdir(parents=True, exist_ok=True)
    (target / "data").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "dashboard/index.html", target / "index.html")
    shutil.copyfile(ROOT / "dashboard/engineering.js", target / "engineering.js")
    shutil.copyfile(ROOT / "dashboard/care.js", target / "care.js")
    shutil.copyfile(source / "care_summary.json", target / "data/care_summary.json")
    for name in CONTRACTS:
        shutil.copyfile(source / name, target / "data" / name)
    (target / "data/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "outputs")
    parser.add_argument("--target", type=Path, default=ROOT / ".runtime/site")
    parser.add_argument("--synthetic", action="store_true", help="Explicitly label invented test fixtures")
    args = parser.parse_args()
    result = build(args.source, args.target, os.environ.get("GITHUB_SHA", "local"), args.synthetic)
    print(f"Release validated: {len(result['tables'])} tables; {result['cohort']['index_patients']:,} index patients; {args.target}")


if __name__ == "__main__":
    main()
