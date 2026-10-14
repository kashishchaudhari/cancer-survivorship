"""Local fixed-model Liver holdout bootstrap; no patient predictions are exported."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from evaluation_design import SEED, partitions
from patient_studies import normalize, read_archive


def evaluate(folder, studies, output):
    study = json.loads((studies / "liver.json").read_text(encoding="utf-8"))
    if study["synthetic"] or study["treatment_assignment"].get("strategy") != "patient":
        raise ValueError("Requires a real-data patient-holdout evaluation")
    raw, source = read_archive(folder, "Liver")
    if source["member_sha256"] != study["source"]["member_sha256"]:
        raise ValueError("Source differs from the fitted study")
    frame = normalize(raw)
    eligible = frame.loc[frame.year.between(2010, 2017) & frame.age_mid.notna()
                         & frame.surgery.isin(["No surgery recorded (00)", "Surgery recorded"])].copy()
    eligible["surgery_target"] = eligible.surgery.eq("Surgery recorded").astype(int)
    development, _, test = partitions(eligible, "surgery_target")
    model = joblib.load(studies / "models/surgery-liver.joblib")["model"]
    probabilities = model.predict_proba(test)[:, 1]
    labels = test.surgery_target.to_numpy()
    if not np.isclose(roc_auc_score(labels, probabilities), study["treatment_assignment"]["test"]["roc_auc"]):
        raise ValueError("Artifact and recorded evaluation disagree")
    rng = np.random.default_rng(SEED + 2)
    scores = []
    for _ in range(1000):
        indices = rng.integers(0, len(labels), len(labels))
        if len(np.unique(labels[indices])) == 2:
            scores.append(roc_auc_score(labels[indices], probabilities[indices]))
    result = {
        "auc_ci": np.quantile(scores, [.025, .975]).tolist(),
        "bootstrap_replicates": len(scores), "seed": SEED + 2,
        "constant_baseline_brier": float(np.mean((labels - development.surgery_target.mean()) ** 2)),
        "scope": "Fixed-model test-sample uncertainty; excludes training and selection uncertainty",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Liver aggregate uncertainty saved locally; no patient rows exported.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--studies", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".runtime/liver-uncertainty.json"))
    args = parser.parse_args()
    evaluate(args.folder, args.studies, args.output)
