import sys
from pathlib import Path

import pandas as pd
import pytest
from lifelines import KaplanMeierFitter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from validate_source_data import independent_km, independent_days
from check_repository_privacy import confidential_path


@pytest.mark.parametrize("times,dead,horizon", [([0,1,1,2,3],[1,1,0,0,1],1),([1,2,3],[0,0,0],2),([1,1],[1,1],2),([1,2,2,3],[0,1,1,0],2)])
def test_independent_km_handles_zero_months_ties_and_censoring(times,dead,horizon):
    times=pd.Series(times,dtype=float)
    dead=pd.Series(dead,dtype=bool)
    actual=independent_km(times,dead,horizon)
    fitted=KaplanMeierFitter().fit(times,dead)
    ci=fitted.confidence_interval_.loc[fitted.confidence_interval_.index<=horizon].iloc[-1]
    assert actual[:3] == pytest.approx([fitted.predict(horizon),ci.iloc[0],ci.iloc[1]],abs=1e-12)
    assert actual[3] == int(times.ge(horizon).sum())


@pytest.mark.parametrize("path",["outputs/km_curves.csv","dashboard/data/manifest.json",".runtime/validation/report.json","data/local/CSRA.xlsx","docs/RESULTS.md","powerbi/report.xlsx","dataset.rar"])
def test_confidential_paths_are_blocked(path):
    assert confidential_path(path)


def test_source_code_is_allowed():
    assert not confidential_path("scripts/build_care_equity.py")
    assert not confidential_path("docs/DATASET_CARD.md")


def test_independent_decoder_preserves_top_coded_timing():
    days=independent_days(pd.Series(["731+ days","000","Unable to calculate"],dtype="string"))
    assert days.iloc[0]==731 and days.iloc[1]==0
    assert pd.isna(days.iloc[2])
