"""Build dashboard-safe aggregates from every raw cancer extract in Datasets.zip.

Patient IDs are kept in memory only for deduplication and linking outcome labels
across extracts. The script writes only aggregate tables, never row-level data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FILES = {
    "Brain": "Datasets/RawBrainCancer.txt",
    "Breast": "Datasets/RawBreastCancer.txt",
    "Liver": "Datasets/RawLiverCancer.txt",
    "Prostate": "Datasets/RawProstateCancer.txt",
    "Skin": "Datasets/RawSkinCancer.txt",
}
PATIENT = "Patient ID"
AGE = "Age recode with <1 year olds"
RACE = "Race recode (W, B, AI, API)"
SEX = "Sex"
YEAR = "Year of diagnosis"
SITE = "Site recode ICD-O-3/WHO 2008"
COD = "COD to site recode"
EVENT_LABEL = "Suicide and Self-Inflicted Injury"


def age_band(value: object) -> str:
    label = str(value).strip().removesuffix(" years")
    if label in {"00", "01-04", "05-09", "10-14", "15-19", "20-24", "25-29",
                 "30-34", "35-39"}:
        return "Under 40"
    if label in {"40-44", "45-49", "50-54", "55-59", "60-64"}:
        return "40-64"
    if label in {"65-69", "70-74", "75-79", "80-84", "85+"}:
        return "65+"
    return "Unknown"


def build(archive: Path) -> None:
    frames: list[pd.DataFrame] = []
    source_stats: dict[str, dict] = {}
    with zipfile.ZipFile(archive) as zf:
        missing = set(FILES.values()) - set(zf.namelist())
        if missing:
            raise ValueError(f"Archive is missing expected extracts: {sorted(missing)}")
        for order, (cohort, member) in enumerate(FILES.items()):
            with zf.open(member) as stream:
                header = pd.read_csv(stream, sep="\t", nrows=0).columns.tolist()
            usecols = [c for c in [PATIENT, AGE, RACE, SEX, YEAR, SITE, COD] if c in header]
            needed = {PATIENT, AGE, RACE, SEX, YEAR, SITE}
            if not needed.issubset(usecols):
                raise ValueError(f"{member} missing required columns: {sorted(needed-set(usecols))}")
            with zf.open(member) as stream:
                frame = pd.read_csv(stream, sep="\t", usecols=usecols, dtype="string",
                                    low_memory=False)
            frame = frame.rename(columns={PATIENT: "patient_id", AGE: "age_raw", RACE: "race",
                                          SEX: "sex", YEAR: "diagnosis_year", SITE: "cancer_site"})
            frame["patient_id"] = frame.patient_id.str.strip()
            frame["diagnosis_year"] = pd.to_numeric(frame.diagnosis_year, errors="coerce")
            for field in ["race", "sex", "cancer_site"]:
                frame[field] = frame[field].astype("string").str.strip().replace("", pd.NA)
            frame["age_band"] = frame.age_raw.map(age_band).astype("string")
            frame["source_cohort"] = cohort
            frame["_cohort_order"] = np.int8(order)
            if COD in frame.columns:
                cause = frame.pop(COD).astype("string").str.strip()
                known = cause.notna() & ~cause.isin(["", "Unknown", "Unknown/Other"])
                frame["_outcome_known"] = known.to_numpy()
                frame["_event"] = cause.eq(EVENT_LABEL).fillna(False).to_numpy(dtype=bool)
            else:
                frame["_outcome_known"] = False
                frame["_event"] = False
            source_stats[cohort] = {
                "source_records": int(len(frame)),
                "records_missing_patient_id": int(frame.patient_id.isna().sum() + frame.patient_id.eq("").sum()),
                "suicide_records_with_outcome_field": int(frame._event.sum()),
                "has_cause_of_death": bool(COD in usecols),
            }
            frames.append(frame.drop(columns=["age_raw"]))
            print(f"Read {cohort}: {len(frame):,} source records", flush=True)

    records = pd.concat(frames, ignore_index=True)
    records = records[records.patient_id.notna() & records.patient_id.ne("")].copy()
    # Outcome is a person-level label. Check all labeled source records before
    # assigning it to the person's earliest cancer diagnosis.
    labeled = records[records._outcome_known]
    per_person_outcome = labeled.groupby("patient_id", sort=False)._event.agg(["min", "max", "size"])
    conflicts = int(per_person_outcome["min"].ne(per_person_outcome["max"]).sum())
    if conflicts:
        raise ValueError(f"Found conflicting outcome labels for {conflicts:,} patients")
    person_outcomes = per_person_outcome["max"].astype(bool)
    records = records.sort_values(["patient_id", "diagnosis_year", "_cohort_order"],
                                  kind="mergesort", na_position="last")
    index = records.drop_duplicates("patient_id", keep="first").copy()
    index["outcome_known"] = index.patient_id.isin(person_outcomes.index)
    index["suicide_event"] = index.patient_id.map(person_outcomes)
    index["outcome_state"] = np.select(
        [~index.outcome_known, index.suicide_event.fillna(False).astype(bool)],
        ["Outcome unavailable", "Suicide outcome recorded"],
        default="No suicide recorded",
    )
    for field in ["source_cohort", "age_band", "race", "sex", "cancer_site"]:
        index[field] = index[field].astype("string").fillna("Unknown")
    index["diagnosis_decade"] = (index.diagnosis_year.floordiv(10) * 10).astype("Int64").astype("string")
    index["diagnosis_decade"] = index.diagnosis_decade.mask(index.diagnosis_decade.eq("<NA>"), "Unknown")

    # Single-grain dashboard fact: one row per combination, count only.
    dimensions = ["source_cohort", "age_band", "sex", "race", "diagnosis_decade", "outcome_state"]
    cube = (index.groupby(dimensions, observed=True, dropna=False)
            .size().rename("patient_count").reset_index())
    cube.to_csv(OUT / "raw_zip_full_eda_cube.csv", index=False)

    # Compact, easy-to-chart margins with separate outcome coverage denominator.
    margins = []
    for dimension in ["source_cohort", "age_band", "sex", "race", "diagnosis_decade"]:
        for category, group in index.groupby(dimension, observed=True, dropna=False):
            known = group[group.outcome_known]
            margins.append({
                "dimension": dimension,
                "category": str(category),
                "unique_patients": int(len(group)),
                "outcome_known_patients": int(len(known)),
                "outcome_unavailable_patients": int((~group.outcome_known).sum()),
                "suicide_patients": int(known.suicide_event.sum()),
                "event_fraction_among_known_outcomes": (
                    float(known.suicide_event.mean()) if len(known) else np.nan
                ),
                "outcome_coverage_fraction": float(group.outcome_known.mean()),
            })
    pd.DataFrame(margins).to_csv(OUT / "raw_zip_full_eda_margins.csv", index=False)

    cohort_counts = (index.groupby("source_cohort", observed=True)
                     .agg(unique_patients=("patient_id", "size"),
                          outcome_known_patients=("outcome_known", "sum"),
                          outcome_unavailable_patients=("outcome_known", lambda s: int((~s).sum())))
                     .reset_index())
    cohort_counts.to_csv(OUT / "raw_zip_full_eda_cohort_counts.csv", index=False)

    summary = {
        "source_records": int(len(records)),
        "unique_patients_across_all_five_extracts": int(len(index)),
        "repeated_records_removed_for_patient_profile": int(len(records) - len(index)),
        "patients_with_outcome_recorded": int(index.outcome_known.sum()),
        "patients_with_outcome_unavailable": int((~index.outcome_known).sum()),
        "suicide_patients_among_known_outcomes": int(index.suicide_event.sum()),
        "event_fraction_among_patients_with_known_outcome": float(index.loc[index.outcome_known, "suicide_event"].mean()),
        "outcome_conflicts": conflicts,
        "index_rule": "Earliest diagnosis year across the five raw extracts; fixed Brain/Breast/Liver/Prostate/Skin order breaks ties.",
        "outcome_rule": "A patient outcome is known if any linked raw record contains cause of death; suicide is the explicit Suicide and Self-Inflicted Injury category. Missing outcome fields are unavailable, never assumed non-suicide.",
        "source_counts": source_stats,
        "power_bi_scope": "Aggregated patient counts only; IDs and row-level records are not written.",
    }
    (OUT / "raw_zip_full_eda_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path,
                        help="Path to local Datasets.zip; raw rows are not extracted or exported")
    args = parser.parse_args()
    build(args.archive)


if __name__ == "__main__":
    main()
