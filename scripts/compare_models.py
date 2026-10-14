"""Tune on development folds, lock the winner, then evaluate untouched test data."""
from pathlib import Path
import json
import time
import warnings
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, roc_auc_score, accuracy_score,
    balanced_accuracy_score, brier_score_loss, confusion_matrix, precision_recall_curve,
    precision_score, recall_score, f1_score, roc_curve, log_loss)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier
from audit_data import OUT, LOCAL, FEATURES

SEED = 20261010


def candidates():
    return {
        "Logistic regression": (LogisticRegression(max_iter=1000, random_state=SEED),
            {"model__C": [0.1, 1.0, 10.0], "model__class_weight": [None, "balanced"]}),
        "Random forest": (RandomForestClassifier(n_estimators=160, n_jobs=2, random_state=SEED),
            {"model__max_depth": [6, None], "model__min_samples_leaf": [25, 100]}),
        "Neural network": (MLPClassifier(max_iter=200, early_stopping=True,
            n_iter_no_change=12, random_state=SEED),
            {"model__hidden_layer_sizes": [(16,), (32, 16)]}),
        "XGBoost": (XGBClassifier(objective="binary:logistic", eval_metric="logloss",
            n_jobs=2, random_state=SEED, tree_method="hist", learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8),
            {"model__max_depth": [2, 4], "model__n_estimators": [150, 300]}),
    }


def positive_probs(estimator, x):
    pos = np.flatnonzero(estimator.classes_ == 1)
    if len(pos) != 1:
        raise ValueError("Missing explicit suicide class 1")
    return estimator.predict_proba(x)[:, pos[0]]


def threshold_f2(y, p):
    precision, recall, threshold = precision_recall_curve(y, p)
    f2 = 5 * precision[:-1] * recall[:-1] / np.maximum(4 * precision[:-1] + recall[:-1], 1e-15)
    # Threshold is chosen entirely from development OOF scores.
    return float(threshold[np.argmax(f2)])


def metrics(y, p, threshold):
    pred = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"roc_auc": roc_auc_score(y, p), "pr_auc_ap": average_precision_score(y, p),
            "brier_score": brier_score_loss(y, p), "log_loss": log_loss(y, p, labels=[0, 1]),
            "accuracy": accuracy_score(y, pred), "balanced_accuracy": balanced_accuracy_score(y, pred),
            "precision": precision_score(y, pred, zero_division=0),
            "recall": recall_score(y, pred, zero_division=0), "f1": f1_score(y, pred, zero_division=0),
            "threshold": threshold, "true_negative": int(tn), "false_positive": int(fp),
            "false_negative": int(fn), "true_positive": int(tp), "test_records": len(y),
            "test_events": int(np.sum(y))}


def group_bootstrap(y, probabilities, groups, reference, replicates=1000):
    unique, inverse = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(SEED)
    results = {name: {"roc_auc": [], "pr_auc_ap": []} for name in probabilities}
    deltas = {name: [] for name in probabilities if name != reference}
    for _ in range(replicates):
        counts = np.bincount(rng.integers(0, len(unique), len(unique)), minlength=len(unique))
        weights = counts[inverse]
        for name, p in probabilities.items():
            results[name]["roc_auc"].append(roc_auc_score(y, p, sample_weight=weights))
            results[name]["pr_auc_ap"].append(average_precision_score(y, p, sample_weight=weights))
        for name in deltas:
            deltas[name].append(results[name]["pr_auc_ap"][-1] - results[reference]["pr_auc_ap"][-1])
    rows = []
    for name, scores in results.items():
        for metric, values in scores.items():
            lo, hi = np.quantile(values, [0.025, 0.975])
            rows.append({"model": name, "metric": metric, "ci_low": lo, "ci_high": hi,
                         "bootstrap_replicates": replicates, "resampling_unit": "exact source profile"})
    contrasts = [{"model": name, "reference": reference, "metric": "PR-AUC difference",
                  "ci_low": np.quantile(v, 0.025), "ci_high": np.quantile(v, 0.975)} for name, v in deltas.items()]
    return pd.DataFrame(rows), pd.DataFrame(contrasts)


def main():
    d = pd.read_csv(LOCAL / "cleaned_cohort.csv", dtype={"duplicate_group": str})
    d = d[d.ml_eligible].reset_index(drop=True)
    x, y, groups = d[FEATURES].astype(str), d.event.astype(int).to_numpy(), d.duplicate_group.to_numpy()
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    dev_idx, test_idx = next(outer.split(x, y, groups))
    xd, xt, yd, yt, gd = x.iloc[dev_idx], x.iloc[test_idx], y[dev_idx], y[test_idx], groups[dev_idx]
    if set(gd) & set(groups[test_idx]) or set(d.row_id.iloc[dev_idx]) & set(d.row_id.iloc[test_idx]):
        raise ValueError("Development/test overlap")
    cv = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED + 1).split(xd, yd, gd))
    for train, val in cv:
        assert not (set(gd[train]) & set(gd[val]))
        assert len(np.unique(yd[train])) == 2 and len(np.unique(yd[val])) == 2
    split = d[["row_id", "duplicate_group", "event"]].copy()
    split["partition"] = "development"
    split.loc[test_idx, "partition"] = "test"
    split.to_csv(LOCAL / "split_manifest.csv", index=False)
    fitted, thresholds, cv_rows, warning_rows = {}, {}, [], []
    for name, (estimator, grid) in candidates().items():
        started = time.time()
        print(f"Tuning {name}: {len(xd):,} development rows, 5 grouped folds", flush=True)
        pipe = Pipeline([("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                         ("model", estimator)])
        search = GridSearchCV(pipe, grid, scoring={"ap": "average_precision", "auc": "roc_auc"},
                              refit="ap", cv=cv, n_jobs=1, error_score="raise", return_train_score=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            search.fit(xd, yd)
            oof = cross_val_predict(clone(search.best_estimator_), xd, yd, cv=cv, n_jobs=1,
                                    method="predict_proba")[:, 1]
        for w in caught:
            warning_rows.append({"model": name, "category": w.category.__name__, "message": str(w.message)})
        fitted[name] = search.best_estimator_
        thresholds[name] = threshold_f2(yd, oof)
        best = search.best_index_
        cv_rows.append({"model": name, "cv_pr_auc_mean": search.best_score_,
                        "cv_pr_auc_sd": search.cv_results_["std_test_ap"][best],
                        "cv_roc_auc_mean": search.cv_results_["mean_test_auc"][best],
                        "cv_train_pr_auc_mean": search.cv_results_["mean_train_ap"][best],
                        "development_oof_threshold": thresholds[name],
                        "parameters": json.dumps(search.best_params_), "seconds": time.time() - started})
        pd.DataFrame(search.cv_results_).to_csv(OUT / f"cv_{name.lower().replace(' ', '_')}.csv", index=False)
        print(f"  CV PR-AUC {search.best_score_:.5f}; threshold {thresholds[name]:.5f}", flush=True)
    cv_table = pd.DataFrame(cv_rows).sort_values("cv_pr_auc_mean", ascending=False)
    winner = str(cv_table.iloc[0].model)
    # Persist selection before generating any test scores.
    (OUT / "selection.json").write_text(json.dumps({"selected_model": winner, "selection_metric": "development 5-fold mean average precision", "seed": SEED}, indent=2), encoding="utf-8")
    cv_table.to_csv(OUT / "cv_comparison.csv", index=False)
    fitted["Prevalence baseline"] = Pipeline([("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ("model", DummyClassifier(strategy="prior"))]).fit(xd, yd)
    thresholds["Prevalence baseline"] = 0.5
    probabilities = {name: positive_probs(m, xt) for name, m in fitted.items()}
    evaluation = pd.DataFrame([{ "model": name, "selected_by_cv": name == winner,
        **metrics(yt, p, thresholds[name])} for name, p in probabilities.items()])
    intervals, contrasts = group_bootstrap(yt, probabilities, groups[test_idx], winner)
    for metric in ["roc_auc", "pr_auc_ap"]:
        ci = intervals[intervals.metric.eq(metric)].set_index("model")
        evaluation[f"{metric}_ci_low"] = evaluation.model.map(ci.ci_low)
        evaluation[f"{metric}_ci_high"] = evaluation.model.map(ci.ci_high)
    evaluation.to_csv(OUT / "model_comparison.csv", index=False)
    intervals.to_csv(OUT / "model_confidence_intervals.csv", index=False)
    contrasts.to_csv(OUT / "paired_model_comparison.csv", index=False)
    pd.DataFrame(warning_rows, columns=["model", "category", "message"]).drop_duplicates().to_csv(OUT / "model_warnings.csv", index=False)
    curve_rows, cal_rows, cutoff_rows = [], [], []
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for name, p in probabilities.items():
        fpr, tpr, _ = roc_curve(yt, p)
        precision, recall, _ = precision_recall_curve(yt, p)
        axes[0].plot(fpr, tpr, label=name)
        axes[1].plot(recall, precision, label=name)
        for a, b in zip(fpr, tpr):
            curve_rows.append({"model": name, "curve": "ROC", "x": a, "y": b})
        for a, b in zip(recall, precision):
            curve_rows.append({"model": name, "curve": "Precision recall", "x": a, "y": b})
        observed, predicted = calibration_curve(yt, p, n_bins=10, strategy="quantile")
        for a, b in zip(predicted, observed):
            cal_rows.append({"model": name, "mean_score": a, "observed_fraction": b})
        cutoff_rows.append({"model": name, "threshold_policy": "default 0.5", **metrics(yt, p, 0.5)})
    axes[0].plot([0, 1], [0, 1], "--", color="gray")
    axes[0].set(xlabel="False positive rate", ylabel="Recall", title="Held-out ROC curves")
    axes[1].axhline(yt.mean(), color="gray", linestyle="--")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Held-out precision recall curves")
    axes[1].legend(fontsize=8)
    fig.savefig(OUT / "model_curves.png", dpi=160)
    plt.close(fig)
    pd.DataFrame(curve_rows).to_csv(OUT / "model_curves.csv", index=False)
    pd.DataFrame(cal_rows).to_csv(OUT / "calibration.csv", index=False)
    pd.DataFrame(cutoff_rows).to_csv(OUT / "default_threshold_metrics.csv", index=False)
    prediction_table = d.iloc[test_idx][["row_id", *FEATURES, "event"]].copy()
    for name, p in probabilities.items():
        prediction_table[name] = p
    prediction_table.to_csv(LOCAL / "test_predictions.csv", index=False)
    subgroups = []
    for col in FEATURES:
        for value in sorted(xt[col].unique()):
            mask = xt[col].eq(value).to_numpy()
            subgroup_y, subgroup_p = yt[mask], probabilities[winner][mask]
            if len(np.unique(subgroup_y)) == 2:
                subgroups.append({"variable": col, "group": value, "model": winner,
                                  "few_events": int(subgroup_y.sum()) < 20,
                                  **metrics(subgroup_y, subgroup_p, thresholds[winner])})
    pd.DataFrame(subgroups).to_csv(OUT / "subgroup_performance.csv", index=False)
    importance = permutation_importance(fitted[winner], xt, yt, n_repeats=5,
        scoring="average_precision", random_state=SEED, n_jobs=1)
    pd.DataFrame({"feature": FEATURES, "importance_mean": importance.importances_mean,
                  "importance_sd": importance.importances_std}).to_csv(OUT / "permutation_importance.csv", index=False)
    joblib.dump(fitted[winner], LOCAL / "selected_model.joblib")
    summary = {"selected_model": winner, "development_rows": len(dev_idx), "test_rows": len(test_idx),
               "development_events": int(yd.sum()), "test_events": int(yt.sum()),
               "test_prevalence": float(yt.mean()), "seed": SEED,
               "primary_predictors": FEATURES, "split": "5-fold StratifiedGroupKFold outer fold 0 held out; 5 grouped development folds",
               "threshold_policy": "development OOF threshold maximizing F2; exploratory only",
               "limitations": ["Outcome-dependent sampled cohort; population risk and calibration cannot be inferred",
                   "No patient identifiers; exact source-profile grouping cannot ensure patient independence",
                   "Binary outcome ignores unequal follow-up and competing deaths",
                   "Threshold OOF estimates follow hyperparameter selection and are not nested unbiased validation estimates",
                   "No external validation; model choice is based on this internal split only"]}
    (OUT / "ml_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(evaluation[["model", "roc_auc", "pr_auc_ap", "precision", "recall"]].to_string(index=False), flush=True)
    print(f"CV-selected model: {winner}", flush=True)


if __name__ == "__main__":
    main()
