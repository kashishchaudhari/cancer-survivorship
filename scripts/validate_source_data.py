"""Independent local reconciliation. No patient rows or identifiers are exported."""
import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from build_raw_zip_dashboard_aggregates import FILES, PATIENT, AGE, YEAR, RACE, SEX, COD, EVENT_LABEL


def choose(conditions, labels, default):
    return np.select([condition.fillna(False).to_numpy(dtype=bool) for condition in conditions],labels,default=default)


def independent_days(labels):
    return pd.to_numeric(labels.replace({"731+ days":"731", "731+":"731"}),errors="coerce")


def independent_km(times, dead, horizon):
    table = pd.DataFrame({"time":times,"death":dead.astype(int)}).groupby("time").agg(exits=("death","size"), deaths=("death","sum")).sort_index()
    risk, estimate, greenwood = len(times), 1.0, 0.0
    for time, row in table.iterrows():
        if time > horizon:
            break
        d = int(row.deaths)
        if d:
            estimate *= 1 - d / risk
            if risk > d:
                greenwood += d / (risk * (risk - d))
        risk -= int(row.exits)
    if estimate in {0, 1}:
        low = high = estimate
    else:
        center = math.log(-math.log(estimate))
        radius = norm.ppf(.975) * math.sqrt(greenwood) / abs(math.log(estimate))
        low, high = math.exp(-math.exp(center+radius)), math.exp(-math.exp(center-radius))
    return estimate, low, high, int((times >= horizon).sum())


def validate(archive: Path, dashboard: Path, report: Path):
    audit = pd.read_csv(dashboard / "care_field_audit.csv")
    expected_counts = audit.groupby("cohort").eligible_patients.first().to_dict()
    evidence = {"status":"running", "confidential":True, "archive":str(archive.resolve()), "members":[], "checks":[], "limitations":["Complete supplied extract is not the complete SEER registry or a population sampling frame.","This verifies calculations, not external validity or treatment causality.","The model test fold has been reused for exploratory configuration comparisons."]}
    h = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            h.update(block)
    evidence["archive_sha256"] = h.hexdigest()
    combined, liver = [], None
    with zipfile.ZipFile(archive) as bundle:
        evidence["additional_archive_members"] = [item.filename for item in bundle.infolist() if not item.is_dir() and item.filename not in FILES.values()]
        for order,(cohort,member) in enumerate(FILES.items()):
            info = bundle.getinfo(member)
            with bundle.open(member) as stream:
                header = pd.read_csv(stream,sep="\t",nrows=0).columns.tolist()
            care_fields = ["Combined Summary Stage (2004+)","Time from diagnosis to treatment in days recode","Median household income inflation adj to 2022","Survival months","Vital status recode (study cutoff used)"]
            wanted = [PATIENT,YEAR,AGE,RACE,SEX,COD] + (care_fields if cohort=="Liver" else [])
            with bundle.open(member) as stream:
                raw = pd.read_csv(stream,sep="\t",usecols=[field for field in wanted if field in header],dtype="string")
            ids = raw[PATIENT].str.strip()
            valid_ids = ids.notna() & ids.ne("")
            raw = raw.loc[valid_ids].copy()
            raw[PATIENT] = ids.loc[valid_ids]
            years = pd.to_numeric(raw[YEAR],errors="coerce")
            index_rows = years.fillna(np.inf).groupby(raw[PATIENT],sort=False).idxmin()
            index = raw.loc[index_rows].copy()
            in_period = pd.to_numeric(index[YEAR],errors="coerce").between(2004,2022)
            observed = int(in_period.sum())
            if observed != expected_counts[cohort]:
                raise ValueError(f"{cohort}: independent index denominator disagrees")
            evidence["members"].append({"cohort":cohort,"member":member,"crc32":format(info.CRC,"08x"),"uncompressed_bytes":info.file_size,"columns":header,"valid_id_records":len(raw),"missing_id_records":int((~valid_ids).sum()),"unique_patients_in_extract":len(index),"period_index_patients":observed,"year_min":int(years.min()),"year_max":int(years.max()),"cause_of_death_present":COD in header})
            raw["source_order"] = order
            raw["source_cohort"] = cohort
            combined.append(raw[[field for field in [PATIENT,YEAR,AGE,RACE,SEX,COD,"source_order","source_cohort"] if field in raw]])
            if cohort=="Liver":
                liver = index.loc[in_period].copy()
            print(f"Verified {cohort} index count against source",flush=True)
    records = pd.concat(combined,ignore_index=True)
    known = records[COD].notna() & ~records[COD].isin(["","Unknown","Unknown/Other"])
    outcomes = records.loc[known,COD].eq(EVENT_LABEL).groupby(records.loc[known,PATIENT]).agg(["min","max"])
    if outcomes["min"].ne(outcomes["max"]).any():
        raise ValueError("Conflicting recorded patient outcomes")
    cube = pd.read_csv(dashboard / "raw_zip_full_eda_cube.csv")
    checks = {"all_index_patients":(int(cube.patient_count.sum()), records[PATIENT].nunique()),"known_outcomes":(int(cube.loc[cube.outcome_state.ne("Outcome unavailable"),"patient_count"].sum()),len(outcomes)),"suicide_outcomes":(int(cube.loc[cube.outcome_state.eq("Suicide outcome recorded"),"patient_count"].sum()),int(outcomes["max"].sum()))}
    for name,(released,independent) in checks.items():
        if released != independent:
            raise ValueError(f"{name}: dashboard does not reconcile with source")
        evidence["checks"].append({"check":name,"status":"passed","count":released})
    index_rows = pd.to_numeric(records[YEAR],errors="coerce").fillna(np.inf).groupby(records[PATIENT],sort=False).idxmin()
    profile = records.loc[index_rows].copy()
    low = pd.to_numeric(profile[AGE].str.extract(r"^(\d+)")[0],errors="coerce")
    profile["age_band"] = choose([low.lt(40),low.between(40,64),low.ge(65)],["Under 40","40-64","65+"],"Unknown")
    profile["sex"] = profile[SEX].str.strip().replace("",pd.NA).fillna("Unknown")
    profile["race"] = profile[RACE].str.strip().replace("",pd.NA).fillna("Unknown")
    decade = (pd.to_numeric(profile[YEAR],errors="coerce")//10*10).astype("Int64").astype("string").replace("<NA>","Unknown")
    profile["diagnosis_decade"] = decade
    profile["outcome_state"] = np.where(~profile[PATIENT].isin(outcomes.index),"Outcome unavailable",np.where(profile[PATIENT].map(outcomes["max"]).fillna(False),"Suicide outcome recorded","No suicide recorded"))
    dimensions = ["source_cohort","age_band","sex","race","diagnosis_decade","outcome_state"]
    for dimension in dimensions:
        profile[dimension] = profile[dimension].astype(str)
        cube[dimension] = cube[dimension].astype(str)
    independent = profile.groupby(dimensions).size().sort_index()
    released = cube.set_index(dimensions).patient_count.sort_index()
    comparison = independent.rename("independent_count").to_frame().join(released.rename("released_count"),how="outer")
    differences = comparison.loc[comparison.independent_count.ne(comparison.released_count)]
    if not differences.empty:
        report.parent.mkdir(parents=True,exist_ok=True)
        differences.to_csv(report.parent / "cube_discrepancies.csv")
        raise ValueError("Independent full descriptive cube does not match dashboard cells")
    evidence["checks"].append({"check":"all_descriptive_cube_cells","status":"passed","cells":len(released)})
    # Independently reconstruct liver group labels without using ETL prepare().
    low_age = pd.to_numeric(liver[AGE].str.extract(r"^(\d+)")[0],errors="coerce")
    liver["age_band"] = choose([low_age.lt(40),low_age.between(40,64),low_age.ge(65)],["Under 40","40-64","65+"],"Unknown")
    income = liver["Median household income inflation adj to 2022"]
    lower = pd.to_numeric(income.str.extract(r"\$([\d,]+)")[0].str.replace(",","",regex=False),errors="coerce")
    lower = lower.mask(income.str.startswith("<",na=False),0)
    liver["income_band"] = choose([lower.lt(50000),lower.between(50000,74999),lower.ge(75000)],["Area median < $50k","Area median $50k–$74,999","Area median ≥ $75k"],"Unknown area income")
    stage = liver["Combined Summary Stage (2004+)"]
    liver["stage_group"] = stage.where(stage.isin(["Localized","Regional","Distant","In situ"]),"Unknown / unavailable")
    timing = independent_days(liver["Time from diagnosis to treatment in days recode"])
    summary = json.loads((dashboard / "care_summary.json").read_text())
    if int(timing.between(0,731).sum()) != summary["timing_known_patients"]:
        raise ValueError("Independent timing availability disagrees")
    time = pd.to_numeric(liver["Survival months"],errors="coerce")
    vital = liver["Vital status recode (study cutoff used)"]
    usable = time.between(0,9998) & vital.isin(["Alive","Dead"])
    if int(usable.sum()) != summary["followup_usable_patients"]:
        raise ValueError("Independent follow-up denominator disagrees")
    errors = []
    for _,row in pd.read_csv(dashboard / "care_survival.csv").iterrows():
        group = liver[row.dimension].eq(row.category) & usable
        computed = independent_km(time.loc[group].astype(float),vital.loc[group].eq("Dead"),row.months)
        for observed,expected in zip([row.survival,row.ci_low,row.ci_high,row.n_risk],computed):
            errors.append(abs(float(observed)-float(expected)))
    if max(errors,default=0)>1e-10:
        raise ValueError("Independent KM/Greenwood calculations disagree")
    evidence["checks"].append({"check":"independent_KM_Greenwood_and_at_risk","status":"passed","estimates":len(errors)//4,"max_absolute_error":max(errors,default=0)})
    evidence["zero_month_followup"] = int((usable & time.eq(0)).sum())
    evidence["care_followup_sensitivity"] = []
    for horizon in [12,36,60]:
        primary = independent_km(time.loc[usable].astype(float),vital.loc[usable].eq("Dead"),horizon)
        positive = usable & time.gt(0)
        excluded = independent_km(time.loc[positive].astype(float),vital.loc[positive].eq("Dead"),horizon)
        evidence["care_followup_sensitivity"].append({"months":horizon,"primary_survival":primary[0],"excluding_zero_month_survival":excluded[0],"patients_at_risk":primary[3],"censored_before_horizon":int((usable & vital.eq("Alive") & time.lt(horizon)).sum()),"interpretation":"Excluding zero-month records changes the population; sensitivity only, not a replacement estimate."})
    evidence["care_missingness_by_group"] = []
    for dimension in ["age_band","income_band","stage_group"]:
        for category, group in liver.groupby(dimension):
            evidence["care_missingness_by_group"].append({"dimension":dimension,"category":category,"patients":len(group),"timing_known":int(timing.loc[group.index].between(0,731).sum()),"followup_usable":int(usable.loc[group.index].sum())})
    evidence["status"] = "passed"
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    print("Independent source reconciliation and survival checks passed. Detailed report stays local.",flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--data",type=Path,default=Path("dashboard/data"))
    parser.add_argument("--report",type=Path,default=Path(".runtime/validation/source_validation.json"))
    args=parser.parse_args()
    validate(args.archive,args.data,args.report)
