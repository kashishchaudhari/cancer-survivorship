"""Temporal model of recorded primary-site surgery coding, never treatment benefit."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def _pipeline(categories, penalty):
    features = ColumnTransformer([
        ("age", SimpleImputer(strategy="median"), ["age_mid"]),
        ("categories", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]), categories),
    ])
    return Pipeline([("features", features), ("model", LogisticRegression(C=penalty, max_iter=1200))])


def _score(model, part):
    probabilities = model.predict_proba(part)[:, 1]
    frame = pd.DataFrame({"predicted": probabilities, "observed": part.surgery_target.to_numpy()})
    frame["bin"] = pd.qcut(frame.predicted, q=5, duplicates="drop")
    calibration = []
    for _, group in frame.groupby("bin", observed=True):
        if len(group) >= 30:
            calibration.append({"n": len(group), "predicted": float(group.predicted.mean()),
                                "observed": float(group.observed.mean())})
    return {
        "average_precision": float(average_precision_score(part.surgery_target, probabilities)),
        "roc_auc": float(roc_auc_score(part.surgery_target, probabilities)),
        "brier": float(brier_score_loss(part.surgery_target, probabilities)),
        "prevalence": float(part.surgery_target.mean()),
        "patients": len(part),
        "positive": int(part.surgery_target.sum()),
        "calibration": calibration,
    }


def train_assignment(frame, cohort, model_dir, synthetic=False):
    """Predict recorded surgery among known 00 vs 01–90 codes on later index years."""
    eligible = frame.loc[
        frame.year.between(2010, 2017)
        & frame.age_mid.notna()
        & frame.surgery.isin(["No surgery recorded (00)", "Surgery recorded"])
    ].copy()
    eligible["surgery_target"] = eligible.surgery.eq("Surgery recorded").astype(int)
    development = eligible.loc[eligible.year.le(2013)]
    validation = eligible.loc[eligible.year.between(2014, 2015)]
    test = eligible.loc[eligible.year.between(2016, 2017)]
    split_counts = {
        name: {"patients": len(part), "surgery_recorded": int(part.surgery_target.sum())}
        for name, part in [("development", development), ("validation", validation), ("test", test)]
    }
    minimum = 30
    if any(len(part) < minimum or part.surgery_target.nunique() < 2 for part in [development, validation, test]):
        return {"status": "Not fitted: insufficient temporal split or class support", "splits": split_counts,
                "target": "Recorded primary-site surgery among known 00 / 01–90 codes", "synthetic": synthetic}

    categories = ["sex", "grade", "income"]
    if eligible.stage.nunique() > 1 and eligible.stage.ne("Unknown / unavailable").any():
        categories.append("stage")
    if cohort == "Breast" and eligible.subtype.nunique() > 1:
        categories.append("subtype")
    candidates = []
    for penalty in [0.01, 0.1, 1.0, 10.0]:
        candidate = _pipeline(categories, penalty).fit(development, development.surgery_target)
        candidates.append({"penalty": penalty, "validation_average_precision": float(
            average_precision_score(validation.surgery_target, candidate.predict_proba(validation)[:, 1]))})
    selected = max(candidates, key=lambda row: row["validation_average_precision"])
    training = pd.concat([development, validation], ignore_index=True)
    model = _pipeline(categories, selected["penalty"]).fit(training, training.surgery_target)
    evaluation = _score(model, test)
    stage_note = ("The Liver source uses its explicit Combined Summary Stage field; the four CancerProject archives do not contain a usable stage field."
                  if cohort == "Liver" and "stage" in categories else
                  "No usable stage field is present in this cohort; grade is not used as a stage proxy.")
    output = Path(model_dir)
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "cohort": cohort, "synthetic": synthetic,
                 "categories": categories, "ages": sorted(float(x) for x in training.age_mid.unique()),
                 "options": {name: sorted(training[name].dropna().astype(str).unique()) for name in categories}},
                output / f"surgery-{cohort.lower()}.joblib")
    return {
        "status": "Fitted / internal temporal evaluation", "synthetic": synthetic,
        "target": "Recorded primary-site surgery among known 00 / 01–90 codes",
        "split_rule": "Index years 2010–2013 development; 2014–2015 validation; 2016–2017 untouched test.",
        "splits": split_counts, "validation_candidates": candidates,
        "selected_penalty": selected["penalty"], "features": ["age_mid", *categories],
        "ages": sorted(float(value) for value in training.age_mid.unique()),
        "options": {name: sorted(training[name].dropna().astype(str).unique()) for name in categories},
        "test": {key: value for key, value in evaluation.items() if key != "calibration"},
        "calibration": evaluation["calibration"],
        "calibration_note": "Brier score is reported beside test prevalence; no individual-level records are exported.",
        "limitations": [
            "This predicts source-recorded surgery assignment, not whether surgery benefits a patient.",
            "Unknown and other surgery codes are excluded; results describe known 00 and 01–90 codes only.",
            stage_note,
            "Clinical eligibility, comorbidity, tumor details, preferences, and treatment-selection reasons are unavailable.",
            "Temporal internal evaluation is not external or clinical validation.",
        ],
    }


def predict_assignment(artifact, values):
    age = float(values.get("age_mid", -1))
    if age not in artifact["ages"]:
        raise ValueError("Select a supported source age-band midpoint")
    row = {"age_mid": age}
    for field in artifact["categories"]:
        value = values.get(field)
        if value not in artifact["options"][field]:
            raise ValueError(f"Unsupported {field} category")
        row[field] = value
    probability = float(artifact["model"].predict_proba(pd.DataFrame([row]))[0, 1])
    return {
        "cohort": artifact["cohort"], "synthetic": artifact["synthetic"],
        "target": "Model estimate of source-recorded primary-site surgery among known codes",
        "probability": probability,
        "interpretation": "Describes historical recording patterns in this dataset. It is not a treatment recommendation or estimate of treatment benefit.",
    }
