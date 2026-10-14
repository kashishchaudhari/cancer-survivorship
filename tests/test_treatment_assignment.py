import sys
from pathlib import Path

import joblib
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from patient_studies import STAGE_FIELDS, fixture, normalize, read_archive
from treatment_assignment import predict_assignment, train_assignment


def test_surgery_model_is_temporal_and_predicts_recorded_codes_only(tmp_path):
    frame = normalize(fixture("Brain", 1400))
    result = train_assignment(frame, "Brain", tmp_path, synthetic=True)

    assert result["status"] == "Fitted / internal temporal evaluation"
    assert result["target"] == "Recorded primary-site surgery among known 00 / 01–90 codes"
    assert result["splits"]["development"]["patients"] > 0
    assert result["splits"]["validation"]["patients"] > 0
    assert result["splits"]["test"]["patients"] > 0
    assert "stage" not in result["features"]
    assert result["test"]["average_precision"] >= 0
    assert result["test"]["brier"] >= 0
    assert all(row["n"] >= 30 for row in result["calibration"])

    artifact = joblib.load(tmp_path / "surgery-brain.joblib")
    profile = {"age_mid": artifact["ages"][0]}
    profile.update({field: values[0] for field, values in artifact["options"].items()})
    estimate = predict_assignment(artifact, profile)
    assert 0 <= estimate["probability"] <= 1
    assert "not a treatment recommendation" in estimate["interpretation"]


def test_unknown_surgery_codes_are_excluded_from_model_population(tmp_path):
    frame = normalize(fixture("Breast", 1400))
    result = train_assignment(frame, "Breast", tmp_path, synthetic=True)
    eligible = frame.loc[frame.year.between(2010, 2017) & frame.age_mid.notna()
                         & frame.surgery.isin(["No surgery recorded (00)", "Surgery recorded"])]
    assert sum(part["patients"] for part in result["splits"].values()) == len(eligible)


def test_stage_is_used_only_when_an_explicit_stage_field_has_values(tmp_path):
    liver = normalize(fixture("Liver", 1400))
    brain = normalize(fixture("Brain", 1400))
    liver_model = train_assignment(liver, "Liver", tmp_path, synthetic=True)
    brain_model = train_assignment(brain, "Brain", tmp_path, synthetic=True)
    assert "stage" in liver_model["features"]
    assert "stage" not in brain_model["features"]


def test_liver_raw_extract_is_fingerprinted_against_zip_member(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    raw_path = source / "RawLiverCancer.txt"
    fixture("Liver", 50).to_csv(raw_path, sep="\t", index=False)
    archive = tmp_path / "Datasets.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.write(raw_path, "Datasets/RawLiverCancer.txt")

    raw, metadata = read_archive(source, "Liver", archive)
    assert metadata["matches_zip_raw_extract"] is True
    assert STAGE_FIELDS[0] in metadata["stage_columns"]
    assert "stage" in normalize(raw)
