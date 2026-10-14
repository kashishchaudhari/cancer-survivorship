import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_care_equity import FIELDS, PATIENT, YEAR, aggregates, income_band, prepare, select_cohort, timing_band


@pytest.mark.parametrize("value,expected", [("000", "Same day"), ("030", "1–30 days"), ("031", "31–60 days"), ("060", "31–60 days"), ("091", "91–730 days"), ("731", "731+ days"), ("999", "Unknown / unavailable"), ("Unable to calculate", "Unknown / unavailable"), ("-5", "Unknown / unavailable")])
def test_timing_keeps_special_values_separate(value, expected):
    assert timing_band(value) == expected


def test_income_is_grouped_without_treating_unknown_as_low():
    assert income_band("Unknown/missing/no match/Not 1990-2022") == "Unknown area income"
    assert income_band("< $35,000") == "Area median < $50k"
    assert income_band("$50,000 - $54,999") == "Area median $50k–$74,999"
    assert income_band("$120,000+") == "Area median ≥ $75k"


def test_index_selection_precedes_period_restriction_and_unknown_followup_excluded():
    # Synthetic test identifiers, never real patient records.
    raw = pd.DataFrame({PATIENT:pd.Series(["fixture-a","fixture-a","fixture-b","fixture-c"],dtype="string"), YEAR:["1999","2010","2008","2009"], FIELDS["survival"]:["12","12","9999","0000"], FIELDS["vital"]:["Dead","Dead","Alive","Dead"]})
    frame = prepare(raw)
    assert set(frame[PATIENT]) == {"fixture-b", "fixture-c"}
    assert frame.followup_usable.tolist() == [False, True]
    assert frame.loc[frame.followup_usable,"months"].iloc[0] == 0


def test_selection_refuses_inadequate_stage_coverage():
    audit = pd.DataFrame([{"cohort":"Fixture","field":field,"usable_fraction":.9 if field!="stage" else .1} for field in ["age","income","timing","stage","survival"]])
    with pytest.raises(ValueError,match="No cohort"):
        select_cohort(audit)


def test_aggregate_export_suppresses_small_counts_and_has_no_ids():
    rows = [{PATIENT:f"fixture-{index}",YEAR:"2010",FIELDS["age"]:"65-69 years",FIELDS["income"]:"$75,000 - $79,999",FIELDS["stage"]:"Localized",FIELDS["timing"]:"010",FIELDS["survival"]:"60",FIELDS["vital"]:"Alive"} for index in range(12)]
    rows.append({**rows[0],PATIENT:"fixture-small",FIELDS["timing"]:"050"})
    raw = pd.DataFrame(rows).astype("string")
    cube, survival = aggregates(prepare(raw),"Fixture")
    assert cube.loc[cube.status.eq("Suppressed"),"patient_count"].isna().all()
    assert int(cube.patient_count.sum()) == 12
    assert PATIENT not in cube and PATIENT not in survival
    assert survival.survival.eq(1).all()
    assert survival.n_risk.ge(11).all()
