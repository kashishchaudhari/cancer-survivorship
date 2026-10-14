"""Audit five local extracts; publish aggregate care-equity research tables only."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

from build_raw_zip_dashboard_aggregates import FILES, AGE, PATIENT, YEAR, age_band

FIELDS = {
    "age": AGE,
    "income": "Median household income inflation adj to 2022",
    "timing": "Time from diagnosis to treatment in days recode",
    "stage": "Combined Summary Stage (2004+)",
    "survival": "Survival months",
    "vital": "Vital status recode (study cutoff used)",
    "chemotherapy": "Chemotherapy recode (yes, no/unk)",
    "radiation": "Radiation recode",
    "surgery": "RX Summ--Surg Prim Site (1998+)",
}
MIN_CELL = 11
PERIOD = (2004, 2022)
ROOT = Path(__file__).resolve().parents[1]


def timing_band(value: object) -> str:
    label = str(value).strip()
    if label in {"731", "731+", "731+ days"}:
        return "731+ days"
    if not re.fullmatch(r"\d{1,3}", label):
        return "Unknown / unavailable"
    days = int(label)
    if days > 730:
        return "Unknown / unavailable"
    if days == 0:
        return "Same day"
    if days <= 30:
        return "1–30 days"
    if days <= 60:
        return "31–60 days"
    if days <= 90:
        return "61–90 days"
    return "91–730 days"


def income_band(value: object) -> str:
    # Never infer an individual's earnings from the area's median income.
    label = str(value).strip()
    if not re.match(r"^(?:<\s*)?\$", label):
        return "Unknown area income"
    numbers = re.findall(r"\d[\d,]*", label)
    if not numbers:
        return "Unknown area income"
    lower = 0 if label.startswith("<") else int(numbers[0].replace(",", ""))
    if lower < 50000:
        return "Area median < $50k"
    if lower < 75000:
        return "Area median $50k–$74,999"
    return "Area median ≥ $75k"


def stage_group(value: object) -> str:
    label = str(value).strip()
    return label if label in {"Localized", "Regional", "Distant", "In situ"} else "Unknown / unavailable"


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    for name in [PATIENT, YEAR, *FIELDS.values()]:
        if name not in frame:
            frame[name] = pd.NA
    frame[PATIENT] = frame[PATIENT].str.strip()
    frame = frame.loc[frame[PATIENT].notna() & frame[PATIENT].ne("")].copy()
    frame["year"] = pd.to_numeric(frame[YEAR], errors="coerce")
    frame = frame.sort_values("year", kind="stable", na_position="last").drop_duplicates(PATIENT)
    # Period restriction follows earliest-record selection, avoiding re-entry.
    frame = frame.loc[frame.year.between(*PERIOD)].copy()
    frame["age_band"] = frame[FIELDS["age"]].map(age_band)
    frame["income_band"] = frame[FIELDS["income"]].map(income_band)
    frame["timing_band"] = frame[FIELDS["timing"]].map(timing_band)
    frame["stage_group"] = frame[FIELDS["stage"]].map(stage_group)
    time = pd.to_numeric(frame[FIELDS["survival"]], errors="coerce")
    frame["followup_usable"] = time.between(0, 9998) & frame[FIELDS["vital"]].isin(["Alive", "Dead"])
    frame["months"] = time.where(frame.followup_usable)
    frame["dead"] = frame[FIELDS["vital"]].eq("Dead").fillna(False)
    return frame


def usable(frame: pd.DataFrame, field: str) -> pd.Series:
    if field == "age":
        return frame.age_band.ne("Unknown")
    if field == "income":
        return frame.income_band.ne("Unknown area income")
    if field == "timing":
        return frame.timing_band.ne("Unknown / unavailable")
    if field == "stage":
        return frame.stage_group.ne("Unknown / unavailable")
    if field in {"survival", "vital"}:
        return frame.followup_usable
    labels = frame[FIELDS[field]].astype("string").str.strip()
    # Combined no/unknown treatment states are not counted as known negatives.
    return labels.notna() & labels.ne("") & ~labels.isin(["99", "999"]) & ~labels.str.contains(r"unknown|no/unk|blank|unable|not applicable", case=False, na=True)


def select_cohort(audit: pd.DataFrame) -> str:
    candidates = []
    for cohort, rows in audit.groupby("cohort"):
        fractions = rows.set_index("field").usable_fraction.to_dict()
        if all(fractions.get(field, 0) >= cutoff for field, cutoff in {"age": .7, "income": .5, "stage": .5, "timing": .3, "survival": .7}.items()):
            candidates.append((min(fractions[field] for field in ["income", "stage", "timing", "survival"]), cohort))
    if not candidates:
        raise ValueError("No cohort meets prespecified coverage thresholds; audit saved, do not fabricate comparisons")
    return max(candidates)[1]


def aggregates(frame: pd.DataFrame, cohort: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    dimensions = ["age_band", "income_band", "stage_group", "timing_band"]
    cube = frame.groupby(dimensions, dropna=False).size().rename("patient_count").reset_index()
    cube.insert(0, "cohort", cohort)
    cube["status"] = np.where(cube.patient_count < MIN_CELL, "Suppressed", "Reported")
    cube["patient_count"] = cube.patient_count.astype("Int64").mask(cube.status.eq("Suppressed"))
    results = []
    for dimension in ["age_band", "income_band", "stage_group"]:
        for group, records in frame.groupby(dimension):
            valid = records.loc[records.followup_usable]
            if len(valid) < MIN_CELL:
                continue
            # Zero-month follow-up is retained at month 0, not recoded to a
            # positive survival duration. All-cause death is the endpoint.
            km = KaplanMeierFitter().fit(valid.months.astype(float), valid.dead.astype(bool))
            for horizon in [12, 36, 60]:
                at_risk = int(valid.months.ge(horizon).sum())
                if at_risk < MIN_CELL:
                    continue
                ci = km.confidence_interval_survival_function_.loc[km.confidence_interval_survival_function_.index <= horizon].iloc[-1]
                results.append({"cohort": cohort, "dimension": dimension, "category": group, "months": horizon,
                                "survival": float(km.predict(horizon)), "ci_low": float(ci.iloc[0]), "ci_high": float(ci.iloc[1]), "n_risk": at_risk})
    return cube, pd.DataFrame(results, columns=["cohort", "dimension", "category", "months", "survival", "ci_low", "ci_high", "n_risk"])


def build(archive: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    audits, frames, source_rows = [], {}, {}
    with zipfile.ZipFile(archive) as bundle:
        for cohort, member in FILES.items():
            if member not in bundle.namelist():
                raise ValueError(f"Missing cancer extract: {member}")
            with bundle.open(member) as stream:
                columns = pd.read_csv(stream, sep="\t", nrows=0).columns.tolist()
            if PATIENT not in columns or YEAR not in columns:
                raise ValueError(f"{cohort}: patient grouping and diagnosis year are required")
            with bundle.open(member) as stream:
                raw = pd.read_csv(stream, sep="\t", usecols=[column for column in [PATIENT, YEAR, *FIELDS.values()] if column in columns], dtype="string", low_memory=False)
            source_rows[cohort] = len(raw)
            frame = prepare(raw)
            del raw
            frames[cohort] = frame
            for field, source in FIELDS.items():
                known = int(usable(frame, field).sum())
                audits.append({"cohort": cohort, "field": field, "source_field": source, "present": int(source in columns), "eligible_patients": len(frame), "usable_patients": known,
                               "usable_fraction": known / len(frame) if len(frame) else 0})
            print(f"Audited {cohort}: {len(frame):,} earliest-index patients in {PERIOD[0]}–{PERIOD[1]}", flush=True)
    audit = pd.DataFrame(audits)
    audit.to_csv(output / "care_field_audit.csv", index=False)
    chosen = select_cohort(audit)
    frame = frames[chosen]
    cube, survival = aggregates(frame, chosen)
    cube.to_csv(output / "care_timing_cube.csv", index=False)
    survival.to_csv(output / "care_survival.csv", index=False)
    summary = {
        "cohort": chosen, "diagnosis_year_start": PERIOD[0], "diagnosis_year_end": PERIOD[1],
        "index_patients": len(frame), "timing_known_patients": int(usable(frame, "timing").sum()),
        "followup_usable_patients": int(frame.followup_usable.sum()), "suppressed_cells": int(cube.status.eq("Suppressed").sum()),
        "displayable_patients": int(cube.patient_count.sum()), "min_cell_count": MIN_CELL,
        "index_rule": "Earliest diagnosis per patient within each source extract, then restrict index year to 2004–2022; stable source order breaks year ties. No cross-extract outcome linkage.",
        "selection_rule": "Coverage: age ≥70%, income ≥50%, stage ≥50%, timing ≥30%, usable follow-up ≥70%; maximize minimum coverage among income, stage, timing, follow-up.",
        "scope": "Descriptive internal analysis of supplied extracts; unadjusted survival comparisons are not treatment effects or population estimates.",
        "timing_definition": "Recorded days to first-course management, possibly an active-surveillance decision; not modality-specific delay or a recommended waiting period.",
        "income_definition": "Area-level median household income proxy from supplied extract; not individual income. Confirm source release/geographic definition before external use.",
        "survival_definition": "Kaplan–Meier all-cause survival from diagnosis by age, area income or stage; usable follow-up only, zero-month observations retained. Estimates shown only with ≥11 patients at risk.",
        "source_rows": source_rows,
    }
    (output / "care_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Selected {chosen}; {len(cube)} aggregate cells; {len(survival)} survival estimates", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs")
    options = parser.parse_args()
    build(options.archive, options.output)
