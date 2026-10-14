"""Reproducible patient-disjoint evaluation within a consistent source era."""
import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split

SEED = 20261014
SPLIT_RULE = (
    "2010–2017 eligible index patients: stratified 80% development / 20% test; "
    "up to five development-only cross-validation folds select regularization. "
    "No patient overlap. Temporal evaluation is a separate sensitivity analysis."
)


def partitions(frame, outcome, strategy="patient"):
    if frame["Patient ID"].duplicated().any():
        raise ValueError("Evaluation requires one index record per patient")
    if strategy == "temporal":
        return (frame.loc[frame.year.le(2013)],
                frame.loc[frame.year.between(2014, 2015)],
                frame.loc[frame.year.between(2016, 2017)])
    if strategy != "patient":
        raise ValueError("Unknown evaluation strategy")
    counts = frame[outcome].value_counts()
    if len(counts) != 2 or counts.min() < 5:
        raise ValueError("Insufficient outcome support for stratified holdout")
    development, test = train_test_split(
        np.arange(len(frame)), test_size=.2, random_state=SEED,
        stratify=frame[outcome].astype(int),
    )
    return frame.iloc[development], None, frame.iloc[test]


def development_folds(frame, outcome):
    folds = min(5, int(frame[outcome].value_counts().min()))
    if folds < 2:
        raise ValueError("Insufficient outcome support for cross-validation")
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED + 1)
    return [(frame.iloc[a], frame.iloc[b]) for a, b in
            splitter.split(frame, frame[outcome].astype(int))]
