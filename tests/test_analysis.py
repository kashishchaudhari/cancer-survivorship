import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pandas as pd
import pytest
from audit_data import age_category, prepare, RENAME
from compare_models import threshold_f2, positive_probs
from sklearn.linear_model import LogisticRegression
import numpy as np


def test_actual_age_labels_and_unknown():
    assert age_category("35-39 years") == "Young"
    assert age_category("40-44 years") == "Middle-aged"
    assert age_category("65-69 years") == "Older"
    assert age_category("85+ years") == "Older"
    assert age_category("Unknown") is None


def test_cleaning_retains_valid_records_and_checks_labels():
    row = ["30-34 years", "Unknown", "Male", "Breast", 2000,
           "Suicide and Self-Inflicted Injury", "0000", "Dead", 1, "Suicide"]
    raw = pd.DataFrame([row, row], columns=RENAME)
    d = prepare(raw)
    assert len(d) == 2 and d.ml_eligible.all()
    assert d.analysis_time.eq(0.5).all()
    assert d.duplicate_group.nunique() == 1 and d.row_id.nunique() == 2
    raw.loc[0, "Event"] = 0
    with pytest.raises(ValueError, match="disagrees"):
        prepare(raw)


def test_probability_direction_and_threshold():
    x = np.array([[-3], [-2], [2], [3]])
    y = np.array([0, 0, 1, 1])
    m = LogisticRegression().fit(x, y)
    p = positive_probs(m, x)
    assert p[-1] > p[0]
    assert 0 <= threshold_f2(y, p) <= 1
