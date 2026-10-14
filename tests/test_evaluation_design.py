import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluation_design import development_folds, partitions
from patient_studies import fixture, normalize


def test_holdout_is_reproducible_disjoint_and_stratified():
    frame = normalize(fixture("Liver", 1000))
    development, validation, test = partitions(frame, "death")
    second, _, second_test = partitions(frame, "death")
    assert validation is None
    assert len(test) == 200
    assert set(development["Patient ID"]).isdisjoint(test["Patient ID"])
    assert set(development["Patient ID"]) | set(test["Patient ID"]) == set(frame["Patient ID"])
    assert development.index.equals(second.index)
    assert test.index.equals(second_test.index)
    assert abs(test.death.mean() - frame.death.mean()) < .01
    checked = []
    for fitting, checking in development_folds(development, "death"):
        assert set(fitting["Patient ID"]).isdisjoint(checking["Patient ID"])
        assert set(checking["Patient ID"]).isdisjoint(test["Patient ID"])
        checked.extend(checking["Patient ID"])
    assert len(checked) == len(set(checked)) == len(development)


def test_duplicates_rejected_and_temporal_sensitivity_preserved():
    frame = normalize(fixture("Liver", 1000))
    frame.loc[frame.index[1], "Patient ID"] = frame.iloc[0]["Patient ID"]
    with pytest.raises(ValueError, match="one index record"):
        partitions(frame, "death")
    frame = normalize(fixture("Liver", 1000))
    development, validation, test = partitions(frame, "death", "temporal")
    assert development.year.le(2013).all()
    assert validation.year.between(2014, 2015).all()
    assert test.year.between(2016, 2017).all()


def test_survival_selection_uses_only_development_and_reports_supported_horizons(tmp_path):
    from patient_survival import train
    result = train(normalize(fixture("Liver", 700)), "Liver", tmp_path, synthetic=True)
    assert result["strategy"] == "patient"
    assert result["cv_folds"] == 5
    assert all(len(row["fold_scores"]) == 5 for row in result["validation_candidates"])
    assert result["splits"]["test"]["patients"] == 140
    for metric in result["evaluation"]["metrics"]:
        if metric["ipcw_brier"] is not None:
            assert metric["support"] == "Supported"
            assert metric["at_risk"] >= 11
