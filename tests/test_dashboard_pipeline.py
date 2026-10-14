import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_dashboard_static import build, validate_table, CONTRACTS
from generate_demo_data import generate


@pytest.fixture
def synthetic_source(tmp_path):
    source = tmp_path / "fixtures"
    generate(source)
    return source


def write_cube(tmp_path, rows, header=None):
    path = tmp_path / "raw_zip_full_eda_cube.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header or CONTRACTS[path.name].split(","))
        writer.writerows(rows)
    return path


@pytest.mark.parametrize("count", ["-1", "nan", "inf", "1.5"])
def test_invalid_counts_rejected(tmp_path, count):
    path = write_cube(tmp_path, [["Brain", "65+", "Male", "Unknown", "2000", "Outcome unavailable", count]])
    with pytest.raises(ValueError):
        validate_table(path)


def test_patient_identifier_column_rejected(tmp_path):
    header = CONTRACTS["raw_zip_full_eda_cube.csv"].split(",") + ["patient_id"]
    path = write_cube(tmp_path, [], header)
    with pytest.raises(ValueError, match="schema"):
        validate_table(path)


def test_duplicate_cells_rejected(tmp_path):
    row = ["Brain", "65+", "Male", "Unknown", "2000", "Outcome unavailable", "12"]
    path = write_cube(tmp_path, [row, row])
    with pytest.raises(ValueError, match="duplicate"):
        validate_table(path)


def test_release_is_allowlisted_and_denominators_reconcile(tmp_path, synthetic_source):
    manifest = build(synthetic_source, tmp_path / "site", "test-revision", synthetic=True)
    cohort = manifest["cohort"]
    assert cohort["index_patients"] == cohort["known_outcomes"] + cohort["unavailable_outcomes"]
    assert cohort["recorded_suicide_outcomes"] <= cohort["known_outcomes"]
    assert {path.name for path in (tmp_path / "site/data").iterdir()} == set(CONTRACTS) | {"manifest.json", "care_summary.json"}
    assert json.loads((tmp_path / "site/data/manifest.json").read_text())["revision"] == "test-revision"


def test_invalid_input_preserves_previous_release(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    target = tmp_path / "site"
    target.mkdir()
    (target / "index.html").write_text("previous release")
    with pytest.raises(FileNotFoundError):
        build(tmp_path / "missing", target)
    assert (target / "index.html").read_text() == "previous release"


def test_release_rejects_unexpected_existing_files(tmp_path, synthetic_source):
    target = tmp_path / "site"
    target.mkdir()
    (target / "private.csv").write_text("private")
    with pytest.raises(ValueError, match="non-allowlisted"):
        build(synthetic_source, target, synthetic=True)


def test_impossible_confidence_interval_rejected(tmp_path):
    path = tmp_path / "km_curves.csv"
    path.write_text(CONTRACTS[path.name] + "\ncancer_site,Brain,60,0.9,0.95,0.98\n")
    with pytest.raises(ValueError, match="confidence interval"):
        validate_table(path)


@pytest.mark.parametrize("count,status", [("5","Reported"),("5","Suppressed"),("12","Unexpected")])
def test_invalid_care_suppression_contract(tmp_path, count, status):
    path = tmp_path / "care_timing_cube.csv"
    path.write_text(CONTRACTS[path.name] + f"\nLiver,65+,Unknown area income,Localized,Same day,{count},{status}\n")
    with pytest.raises(ValueError):
        validate_table(path)


def test_suppressed_care_counts_remain_missing(tmp_path):
    path = tmp_path / "care_timing_cube.csv"
    path.write_text(CONTRACTS[path.name] + "\nLiver,65+,Unknown area income,Localized,Same day,,Suppressed\n")
    assert validate_table(path)[0]["patient_count"] == ""


def test_synthetic_fixtures_cannot_be_presented_as_research(tmp_path, synthetic_source, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(ValueError, match="explicitly labeled"):
        build(synthetic_source,tmp_path / "site")


def test_real_build_is_blocked_on_hosted_ci(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS","true")
    with pytest.raises(ValueError,match="Hosted CI"):
        build(tmp_path / "source",tmp_path / "site")
