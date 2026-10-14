"""Compare diagnosis-time predictors on the full, ID-bearing SEER extracts.

Patient identifiers are read only to choose one earliest included cancer record
per person and keep patients together during the grouped split. Identifiers and
row-level predictions are never written to project outputs.
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from audit_data import OUT

SEED = 20261010
CONTROL_SAMPLE_RATE = 1.0
FILES = {
    "Brain": "Datasets/RawBrainCancer.txt",
    "Breast": "Datasets/RawBreastCancer.txt",
    "Liver": "Datasets/RawLiverCancer.txt",
    "Prostate": "Datasets/RawProstateCancer.txt",
}

SOURCE_COLUMNS = {
    "Patient ID",
    "Age recode with <1 year olds",
    "Race recode (W, B, AI, API)",
    "Sex",
    "Site recode ICD-O-3/WHO 2008",
    "Year of diagnosis",
    "COD to site recode",
    "Primary Site",
    "Histologic Type ICD-O-3",
    "Grade Recode (thru 2017)",
    "Laterality",
    "RX Summ--Surg Prim Site (1998+)",
    "Radiation recode",
    "Chemotherapy recode (yes, no/unk)",
    "Marital status at diagnosis",
    "Median household income inflation adj to 2022",
}
RENAME = {
    "Patient ID": "patient_id",
    "Age recode with <1 year olds": "age_raw",
    "Race recode (W, B, AI, API)": "race",
    "Sex": "sex",
    "Site recode ICD-O-3/WHO 2008": "cancer_site",
    "Year of diagnosis": "diagnosis_year",
    "COD to site recode": "cause_of_death",
    "Primary Site": "primary_site",
    "Histologic Type ICD-O-3": "histology",
    "Grade Recode (thru 2017)": "grade",
    "Laterality": "laterality",
    "RX Summ--Surg Prim Site (1998+)": "surgery",
    "Radiation recode": "radiation",
    "Chemotherapy recode (yes, no/unk)": "chemotherapy",
    "Marital status at diagnosis": "marital_status",
    "Median household income inflation adj to 2022": "income",
}
BASE = ["age_cat", "sex", "race", "cancer_site"]
DIAGNOSIS_NO_YEAR = BASE + [
    "primary_site", "histology", "grade", "laterality", "marital_status", "income",
]
DIAGNOSIS = DIAGNOSIS_NO_YEAR + ["diagnosis_year"]
TREATMENT = DIAGNOSIS + ["surgery", "radiation", "chemotherapy"]
FEATURE_SETS = {
    "Baseline 4 features": BASE,
    "Diagnosis details, no diagnosis year": DIAGNOSIS_NO_YEAR,
    "Diagnosis details plus year": DIAGNOSIS,
    "Diagnosis details, year and treatment": TREATMENT,
}


def age_category(label: object) -> str:
    text = str(label).strip().removesuffix(" years")
    if text in {"00", "01-04", "05-09", "10-14", "15-19", "20-24", "25-29",
                "30-34", "35-39"}:
        return "Young"
    if text in {"40-44", "45-49", "50-54", "55-59", "60-64"}:
        return "Middle-aged"
    if text in {"65-69", "70-74", "75-79", "80-84", "85+"}:
        return "Older"
    return "Unknown"


def load_cohort(archive: Path, control_sample_rate: float = CONTROL_SAMPLE_RATE
                ) -> tuple[pd.DataFrame, dict]:
    if not 0.01 <= control_sample_rate <= 1.0:
        raise ValueError("control_sample_rate must be between 0.01 and 1.0")
    parts = []
    source_counts = {}
    all_raw_suicide_ids: set[str] = set()
    all_raw_control_ids: set[str] = set()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        missing = set(FILES.values()) - names
        if missing:
            raise ValueError(f"Archive is missing expected extracts: {sorted(missing)}")
        for cohort, member in FILES.items():
            with zf.open(member) as stream:
                frame = pd.read_csv(stream, sep="\t", usecols=list(SOURCE_COLUMNS),
                                    dtype="string", low_memory=False)
            frame = frame.rename(columns=RENAME)
            frame["patient_id"] = frame.patient_id.str.strip()
            frame["diagnosis_year"] = pd.to_numeric(frame.diagnosis_year, errors="coerce")
            frame["event"] = frame.cause_of_death.eq(
                "Suicide and Self-Inflicted Injury").astype("int8")
            frame["age_cat"] = frame.age_raw.map(age_category).astype("string")
            frame["source_cohort"] = cohort
            raw_records = len(frame)
            raw_suicide_records = int(frame.event.sum())
            raw_unique_patients = int(frame.patient_id.nunique())
            all_raw_suicide_ids.update(frame.loc[frame.event.eq(1), "patient_id"].array)
            all_raw_control_ids.update(frame.loc[frame.event.eq(0), "patient_id"].array)
            # Retain every event patient and a deterministic sample of
            # controls. The default rate of 1.0 uses every patient. Lower rates
            # support memory-limited runs; inverse-probability weights restore
            # source-cohort prevalence in those sampled runs.
            id_hash = pd.util.hash_pandas_object(
                frame.patient_id, index=False, hash_key="0123456789123456"
            ).to_numpy(dtype=np.uint64)
            selected = frame.event.eq(1).to_numpy() | (
                id_hash % 100 < int(control_sample_rate * 100)
            )
            frame = frame.loc[selected].copy()
            frame["sample_weight"] = np.where(
                frame.event.eq(1), 1.0, 1.0 / control_sample_rate
            ).astype("float32")
            source_counts[cohort] = {
                "raw_records": int(raw_records),
                "raw_suicide_records": raw_suicide_records,
                "raw_unique_patient_ids": raw_unique_patients,
                "sampled_records": int(len(frame)),
                "suicide_records": int(frame.event.sum()),
                "sampled_unique_patient_ids": int(frame.patient_id.nunique()),
            }
            parts.append(frame.drop(columns=["age_raw", "cause_of_death"]))
            print(f"Read {cohort}: {len(frame):,} cancer records; "
                  f"{int(frame.event.sum()):,} suicide records", flush=True)
    data = pd.concat(parts, ignore_index=True)
    raw_outcome_conflicts = len(all_raw_suicide_ids & all_raw_control_ids)
    if raw_outcome_conflicts:
        raise ValueError(f"Outcome conflicts across raw records for {raw_outcome_conflicts:,} patients")
    if data.patient_id.isna().any() or data.patient_id.eq("").any():
        raise ValueError("Patient ID is missing in one or more source rows")
    per_patient_events = data.groupby("patient_id", sort=False).event.nunique()
    conflicts = int(per_patient_events.gt(1).sum())
    if conflicts:
        raise ValueError(f"Outcome conflicts across records for {conflicts:,} patients")

    # Use the earliest diagnosis among these four cancer cohorts as each person's
    # index record. Break same-year ties by a fixed cohort order.
    cohort_order = {name: i for i, name in enumerate(FILES)}
    data["_cohort_order"] = data.source_cohort.map(cohort_order).astype("int8")
    data = data.sort_values(["patient_id", "diagnosis_year", "_cohort_order"],
                            kind="mergesort", na_position="last")
    record_count = len(data)
    data = data.drop_duplicates("patient_id", keep="first").reset_index(drop=True)
    repeated = record_count - len(data)
    if data.patient_id.duplicated().any():
        raise ValueError("Expected one index record per patient")
    summary = {
        "raw_source_records": int(sum(s["raw_records"] for s in source_counts.values())),
        "raw_unique_patient_ids": int(len(all_raw_suicide_ids) + len(all_raw_control_ids)),
        "raw_unique_suicide_patients": int(len(all_raw_suicide_ids)),
        "raw_repeated_records_beyond_first": int(
            sum(s["raw_records"] for s in source_counts.values())
            - len(all_raw_suicide_ids) - len(all_raw_control_ids)
        ),
        "raw_event_prevalence": float(
            len(all_raw_suicide_ids) / (len(all_raw_suicide_ids) + len(all_raw_control_ids))
        ),
        "sampled_source_records_before_patient_collapse": record_count,
        "unique_patients": int(len(data)),
        "repeated_sample_records_removed": int(repeated),
        "patient_level_suicide_events": int(data.event.sum()),
        "sample_patient_event_prevalence": float(data.event.mean()),
        "negative_patient_sampling_probability": control_sample_rate,
        "model_cohort_is_full": bool(control_sample_rate == 1.0),
        "sampled_records_beyond_first": int(repeated),
        "patients_with_outcome_conflicts": raw_outcome_conflicts,
        "source_counts": source_counts,
        "index_record_rule": "Earliest diagnosis year among Brain, Breast, Liver, and Prostate records; fixed cohort order breaks same-year ties",
    }
    summary["weighted_source_event_prevalence"] = float(
        np.average(data.event, weights=data.sample_weight)
    )
    return data, summary


def metric_row(name: str, feature_set: str, y: np.ndarray, probability: np.ndarray,
               sample_prevalence: float, source_prevalence: float,
               weights: np.ndarray, duration: float) -> dict:
    return {
        "model": name,
        "feature_set": feature_set,
        "roc_auc": float(roc_auc_score(y, probability, sample_weight=weights)),
        "average_precision": float(average_precision_score(y, probability, sample_weight=weights)),
        "sample_average_precision": float(average_precision_score(y, probability)),
        "sample_test_prevalence": sample_prevalence,
        "weighted_test_prevalence": source_prevalence,
        "average_precision_lift_over_weighted_prevalence": float(
            average_precision_score(y, probability, sample_weight=weights) / source_prevalence
        ),
        "fit_seconds": duration,
    }


def paired_bootstrap(y: np.ndarray, predictions: dict[str, np.ndarray],
                     sample_weights: np.ndarray, replicates: int = 500
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Patient bootstrap with inverse-probability weights for sampled controls."""
    rng = np.random.default_rng(SEED + 2)
    n = len(y)
    selected = {
        "XGBoost | Baseline 4 features": predictions["XGBoost | Baseline 4 features"],
        "XGBoost | Diagnosis details, no diagnosis year": predictions[
            "XGBoost | Diagnosis details, no diagnosis year"],
        "XGBoost | Diagnosis details plus year": predictions[
            "XGBoost | Diagnosis details plus year"],
        "XGBoost | Diagnosis details, year and treatment": predictions[
            "XGBoost | Diagnosis details, year and treatment"],
    }
    per_model = {name: {"roc_auc": [], "average_precision": []}
                 for name in selected}
    contrasts = {
        "Diagnosis details (no year) minus baseline": (
            "XGBoost | Diagnosis details, no diagnosis year", "XGBoost | Baseline 4 features"),
        "Adding diagnosis year": (
            "XGBoost | Diagnosis details plus year",
            "XGBoost | Diagnosis details, no diagnosis year"),
        "Adding treatment fields": (
            "XGBoost | Diagnosis details, year and treatment",
            "XGBoost | Diagnosis details plus year"),
    }
    delta_values = {name: {"roc_auc": [], "average_precision": []}
                    for name in contrasts}
    for _ in range(replicates):
        multiplicity = np.bincount(rng.integers(0, n, n), minlength=n)
        weights = sample_weights * multiplicity
        scores = {}
        for name, probability in selected.items():
            scores[name] = {
                "roc_auc": roc_auc_score(y, probability, sample_weight=weights),
                "average_precision": average_precision_score(y, probability,
                                                              sample_weight=weights),
            }
            for metric, value in scores[name].items():
                per_model[name][metric].append(value)
        for contrast, (left, right) in contrasts.items():
            for metric in ("roc_auc", "average_precision"):
                delta_values[contrast][metric].append(
                    scores[left][metric] - scores[right][metric])
    intervals = []
    for model, metrics_by_model in per_model.items():
        for metric, values in metrics_by_model.items():
            intervals.append({"model": model, "metric": metric,
                              "ci_low": float(np.quantile(values, 0.025)),
                              "ci_high": float(np.quantile(values, 0.975)),
                              "bootstrap_replicates": replicates,
                              "resampling_unit": "held-out patient"})
    differences = []
    for contrast, metrics_by_contrast in delta_values.items():
        for metric, values in metrics_by_contrast.items():
            differences.append({"contrast": contrast, "metric": f"{metric} difference",
                                "estimate": float(np.mean(values)),
                                "ci_low": float(np.quantile(values, 0.025)),
                                "ci_high": float(np.quantile(values, 0.975)),
                                "bootstrap_replicates": replicates,
                                "resampling_unit": "held-out patient"})
    return pd.DataFrame(intervals), pd.DataFrame(differences)


def compare(data: pd.DataFrame, summary: dict
            ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = data.event.to_numpy(dtype=np.int8)
    groups = data.patient_id.to_numpy()
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    development_idx, test_idx = next(outer.split(data[BASE], labels, groups))
    train, test = data.iloc[development_idx], data.iloc[test_idx]
    if set(train.patient_id) & set(test.patient_id):
        raise ValueError("Patient ID crossed development/test split")
    y_train, y_test = labels[development_idx], labels[test_idx]
    sample_weights_train = train.sample_weight.to_numpy(dtype=np.float32)
    sample_weights_test = test.sample_weight.to_numpy(dtype=np.float32)
    weighted_source_prevalence = float(np.average(y_test, weights=sample_weights_test))
    summary.update({
        "development_patients": int(len(train)),
        "test_patients": int(len(test)),
        "development_events": int(y_train.sum()),
        "test_events": int(y_test.sum()),
        "development_prevalence": float(y_train.mean()),
        "test_prevalence": float(y_test.mean()),
        "test_weighted_prevalence": weighted_source_prevalence,
        "split": "One held-out fold from 5-fold StratifiedGroupKFold, grouped by Patient ID; four folds for development",
    })
    rows = []
    predictions = {}
    for feature_set, features in FEATURE_SETS.items():
        encoder = ColumnTransformer([
            ("categorical", OneHotEncoder(handle_unknown="ignore", min_frequency=20,
                                            sparse_output=True, dtype=np.float32), features),
        ], remainder="drop", sparse_threshold=1.0)
        x_train = encoder.fit_transform(train[features].fillna("Missing").astype("string"))
        x_test = encoder.transform(test[features].fillna("Missing").astype("string"))
        models = [
            ("Logistic regression", LogisticRegression(
                max_iter=500, solver="liblinear", class_weight=None,
                random_state=SEED)),
            ("XGBoost", XGBClassifier(
                objective="binary:logistic", eval_metric="logloss", n_estimators=250,
                max_depth=4, learning_rate=0.05, min_child_weight=10, subsample=0.8,
                colsample_bytree=0.8, scale_pos_weight=1, reg_lambda=2,
                n_jobs=2, random_state=SEED, tree_method="hist")),
        ]
        print(f"Feature set {feature_set}: {x_train.shape[0]:,} train rows, "
              f"{x_train.shape[1]:,} encoded columns", flush=True)
        for name, model in models:
            start = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                model.fit(x_train, y_train, sample_weight=sample_weights_train)
            elapsed = time.perf_counter() - start
            probability = model.predict_proba(x_test)[:, 1]
            predictions[f"{name} | {feature_set}"] = probability
            rows.append(metric_row(name, feature_set, y_test, probability,
                                   float(y_test.mean()), weighted_source_prevalence,
                                   sample_weights_test, elapsed))
            if caught:
                print(f"  {name}: {len(caught)} convergence warning(s)", flush=True)
            print(f"  {name}: ROC-AUC={rows[-1]['roc_auc']:.4f}, "
                  f"weighted AP={rows[-1]['average_precision']:.5f}, "
                  f"weighted lift={rows[-1]['average_precision_lift_over_weighted_prevalence']:.2f}x, "
                  f"fit={elapsed:.1f}s", flush=True)
    intervals, differences = paired_bootstrap(y_test, predictions, sample_weights_test)
    summary["bootstrap_replicates"] = 500
    return pd.DataFrame(rows), intervals, differences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True,
                        help="Path to the local Datasets.zip; it is read without extracting raw records")
    parser.add_argument("--control-sample-rate", type=float, default=CONTROL_SAMPLE_RATE,
                        help="Fraction of non-event patients to retain (default: 1.0, all patients)")
    args = parser.parse_args()
    if not args.archive.is_file():
        raise FileNotFoundError(args.archive)
    OUT.mkdir(exist_ok=True)
    data, summary = load_cohort(args.archive, args.control_sample_rate)
    results, intervals, differences = compare(data, summary)
    results.to_csv(OUT / "raw_zip_model_comparison.csv", index=False)
    intervals.to_csv(OUT / "raw_zip_model_confidence_intervals.csv", index=False)
    differences.to_csv(OUT / "raw_zip_paired_differences.csv", index=False)
    (OUT / "raw_zip_analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print("\nPatient-level audit:")
    print(json.dumps(summary, indent=2))
    print("\nSaved aggregate-only results to outputs/raw_zip_model_comparison.csv")


if __name__ == "__main__":
    main()
