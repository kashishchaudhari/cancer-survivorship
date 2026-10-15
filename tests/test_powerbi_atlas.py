import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_powerbi_atlas import build, m_literal, model_definition, write_project
from check_powerbi_project import inspect_project


def test_public_powerbi_project_is_complete_and_synthetic():
    result = inspect_project(ROOT / "powerbi/PatientAtlas")
    assert result["pages"] == 7
    assert result["tables"] == 8
    assert result["visuals"] >= 40
    assert result["synthetic"] is True


def test_real_powerbi_build_cannot_target_public_folder():
    # Must fail before any file is written, even if the private input is incomplete.
    with pytest.raises(ValueError, match="ignored .runtime"):
        build([{"synthetic": False}], ROOT / "powerbi/not-permitted", synthetic=False)
    with pytest.raises(ValueError, match="ignored .runtime"):
        write_project({}, ROOT / "powerbi/not-permitted", synthetic=False)
    assert not (ROOT / "powerbi/not-permitted").exists()


def test_powerbi_model_does_not_average_metrics_or_mix_treatment_modalities():
    data = json.loads((ROOT / "powerbi/PatientAtlas/aggregate-data.json").read_text(encoding="utf-8"))
    model = model_definition(data["tables"], True)
    measures = {m["name"]: m["expression"] for m in model["model"]["tables"][0]["measures"]}
    for name in ["Surgery ROC AUC", "Surgery average precision", "Surgery Brier", "Survival C-index", "Index patients"]:
        assert "HASONEVALUE(Cohorts[Cohort])" in measures[name]
        assert "AVERAGE(" not in measures[name]
    assert "HASONEVALUE(Modalities[Modality])" in measures["Recorded treatment patients"]


def test_m_literals_escape_quotes_and_do_not_execute_m_escape_sequences():
    assert m_literal('A "quoted" label') == '"A ""quoted"" label"'
    assert m_literal("#(lf)") == '"#(#)(lf)"'
    assert m_literal(None) == "null"
    with pytest.raises(ValueError, match="Nonfinite"):
        m_literal(float("nan"))
