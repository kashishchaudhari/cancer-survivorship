"""Five independent cancer-patient studies. No patient data is exported to Git."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

ARCHIVES = {
    "Brain": ("BrainCancerProjectSpring2025.rar", "BrainCancerProjectSpring2025.txt", "RawBrainCancer.txt"),
    "Breast": ("BreatCancerProjectSpring2025.rar", "BreatCancerProjectSpring2025.txt", "RawBreastCancer.txt"),
    "Prostate": ("ProstateCancerProject2025.rar", "ProstateCancerProject2025.txt", "RawProstateCancer.txt"),
    "Skin": ("SkinCancerProjectSpring2025.rar", "SkinCancerProjectSpring2025.txt", "RawSkinCancer.txt"),
    "Liver": ("RawLiverCancer.txt", None, "RawLiverCancer.txt"),
}
ID = "Patient ID"
YEAR = "Year of diagnosis"
AGE = "Age recode with <1 year olds"
SEX = "Sex"
GRADE = "Grade Recode (thru 2017)"
INCOME = "Median household income inflation adj to 2022"
TIME = "Survival months"
VITAL = "Vital status recode (study cutoff used)"
TIMING = "Time from diagnosis to treatment in days recode"
SURGERY = "RX Summ--Surg Prim Site (1998+)"
CHEMO = "Chemotherapy recode (yes, no/unk)"
RADIATION = "Radiation recode"
SUBTYPE = "Breast Subtype (2010+)"
FIELDS = [ID,YEAR,AGE,SEX,GRADE,INCOME,TIME,VITAL,TIMING,SURGERY,CHEMO,RADIATION,SUBTYPE]
STAGE_FIELDS = ["Combined Summary Stage (2004+)","Summary stage 2000 (1998-2017)","Derived AJCC Stage Group, 7th ed (2010-2015)"]


def age_midpoint(label):
    text=str(label).strip().removesuffix(" years")
    if text=="00": return 0.5
    match=re.fullmatch(r"(\d+)-(\d+)",text)
    if match: return (int(match[1])+int(match[2]))/2
    if text=="85+": return 87.5
    return np.nan


def grade_group(label):
    text=str(label).strip()
    for numeral,number in [("IV",4),("III",3),("II",2),("I",1)]:
        if re.search(rf"\bGrade {numeral}\b",text,re.I): return f"Grade {number}"
    return "Unknown / unavailable"


def income_group(label):
    text=str(label).strip()
    match=re.search(r"\$([\d,]+)",text)
    if not match: return "Unknown"
    low=0 if text.startswith("<") else int(match[1].replace(",",""))
    return "< $50k" if low<50000 else "$50k–$74,999" if low<75000 else "≥ $75k"


def surgery_group(label):
    text=str(label).strip()
    if text in {"00","0"}: return "No surgery recorded (00)"
    if re.fullmatch(r"\d{1,2}",text) and 1<=int(text)<=90: return "Surgery recorded"
    return "Unknown / other code"


def normalize(raw):
    frame=raw.copy()
    for field in FIELDS:
        if field not in frame: frame[field]=pd.NA
    frame[ID]=frame[ID].astype("string").str.strip()
    frame=frame.loc[frame[ID].notna() & frame[ID].ne("")].copy()
    frame["year"]=pd.to_numeric(frame[YEAR],errors="coerce")
    frame=frame.sort_values("year",kind="stable",na_position="last").drop_duplicates(ID).copy()
    frame["age_mid"]=frame[AGE].map(age_midpoint)
    frame["age_band"]=np.select([frame.age_mid.lt(40),frame.age_mid.between(40,64),frame.age_mid.ge(65)],["Under 40","40–64","65+"],default="Unknown")
    frame["sex"]=frame[SEX].astype("string").fillna("Unknown")
    frame["grade"]=frame[GRADE].map(grade_group)
    frame["income"]=frame[INCOME].map(income_group)
    duration=pd.to_numeric(frame[TIME],errors="coerce").astype(float)
    frame["followup_valid"]=duration.between(0,9998) & frame[VITAL].isin(["Alive","Dead"])
    frame["months"]=duration.where(frame.followup_valid)
    frame["death"]=frame[VITAL].eq("Dead").fillna(False)
    # Cox requires positive durations; midpoint of the recorded zero-month interval.
    frame["model_months"]=frame.months.clip(lower=.5)
    timing=pd.to_numeric(frame[TIMING].replace({"731+ days":"731","731+":"731"}),errors="coerce")
    frame["timing_days"]=timing.where(timing.between(0,730))
    frame["timing_capped"]=timing.eq(731)
    frame["surgery"]=frame[SURGERY].map(surgery_group)
    frame["chemotherapy"]=frame[CHEMO].astype("string").fillna("Unknown")
    frame["radiation"]=frame[RADIATION].astype("string").fillna("Unknown")
    frame["subtype"]=frame[SUBTYPE].astype("string").fillna("Unknown / unavailable")
    available_stage=next((field for field in STAGE_FIELDS if field in frame.columns),None)
    frame["stage"]=frame[available_stage].astype("string").fillna("Unknown / unavailable") if available_stage else "Unknown / unavailable"
    return frame


def stream_hash(stream):
    digest=hashlib.sha256()
    for block in iter(lambda:stream.read(8*1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def read_archive(folder,cohort,zip_path=None):
    archive,member,zip_member=ARCHIVES[cohort]
    path=folder/archive
    if member is None:
        with path.open("rb") as stream:
            header=next(csv.reader([stream.readline().decode("utf-8-sig")],delimiter="\t"))
        if ID not in header or YEAR not in header: raise ValueError(f"{archive}: patient ID and year required")
        raw=pd.read_csv(path,sep="\t",usecols=lambda field:field in FIELDS+STAGE_FIELDS,dtype="string")
        with path.open("rb") as stream: digest=stream_hash(stream)
        matching=None
        if zip_path:
            with zipfile.ZipFile(zip_path) as bundle:
                with bundle.open("Datasets/"+zip_member) as stream: matching=stream_hash(stream)==digest
        return raw,{"archive":"Local raw extract","member":archive,"member_sha256":digest,"matches_zip_raw_extract":matching,"source_rows":len(raw),"columns":header,"stage_columns":[field for field in STAGE_FIELDS if field in header]}
    # Full extraction is streamed to memory; no raw text is written to workspace.
    process=subprocess.Popen(["tar","-xOf",str(path),member],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    header=next(csv.reader([process.stdout.readline().decode("utf-8-sig")],delimiter="\t"))
    if ID not in header or YEAR not in header: raise ValueError(f"{archive}: patient ID and year required")
    raw=pd.read_csv(process.stdout,sep="\t",names=header,header=None,usecols=[field for field in FIELDS+STAGE_FIELDS if field in header],dtype="string")
    errors=process.stderr.read().decode(errors="replace")
    if process.wait()!=0: raise ValueError(f"Could not read {archive}: {errors}")
    process=subprocess.Popen(["tar","-xOf",str(path),member],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    digest=stream_hash(process.stdout)
    errors=process.stderr.read().decode(errors="replace")
    if process.wait()!=0: raise ValueError(f"Could not fingerprint {archive}: {errors}")
    matching=None
    if zip_path:
        with zipfile.ZipFile(zip_path) as bundle:
            with bundle.open("Datasets/"+zip_member) as stream: matching=stream_hash(stream)==digest
    return raw,{"archive":archive,"member":member,"member_sha256":digest,"matches_zip_raw_extract":matching,"source_rows":len(raw),"columns":header,"stage_columns":[field for field in STAGE_FIELDS if field in header]}


def histogram(values,edges):
    counts,_=np.histogram(values.dropna().astype(float),bins=edges)
    return [{"left":float(a),"right":float(b),"count":int(n)} for a,b,n in zip(edges[:-1],edges[1:],counts)]


def stats(values):
    numbers=values.dropna().astype(float)
    if len(numbers)<11: return {"n":len(numbers),"suppressed":True}
    return {"n":len(numbers),"mean":float(numbers.mean()),"std":float(numbers.std(ddof=1)),"variance":float(numbers.var(ddof=1)),"p05":float(numbers.quantile(.05)),"q1":float(numbers.quantile(.25)),"median":float(numbers.median()),"q3":float(numbers.quantile(.75)),"p95":float(numbers.quantile(.95)),"min":float(numbers.min()),"max":float(numbers.max())}


def categories(values):
    return [{"label":str(label),"count":int(count) if count>=11 else None,"status":"Reported" if count>=11 else "Suppressed"} for label,count in values.value_counts(dropna=False).items()]


def profile(frame,age="All",sex="All",grade="All",stage="All"):
    selected=frame
    for field,value in [("age_band",age),("sex",sex),("grade",grade),("stage",stage)]:
        if value!="All": selected=selected.loc[selected[field].eq(value)]
    if len(selected)<11: return {"age":age,"sex":sex,"grade":grade,"stage":stage,"n":None,"suppressed":True}
    timing=selected.timing_days
    valid=selected.loc[selected.followup_valid]
    curves=[]
    if len(valid)>=11:
        km=KaplanMeierFitter().fit(valid.model_months.astype(float),valid.death.astype(bool))
        for month in range(0,121,3):
            n_risk=int(valid.model_months.ge(month).sum())
            if n_risk<11: break
            ci=km.confidence_interval_.loc[km.confidence_interval_.index<=month].iloc[-1]
            curves.append({"months":month,"survival":float(km.predict(month)),"low":float(ci.iloc[0]),"high":float(ci.iloc[1]),"at_risk":n_risk})
    age_labels=selected[AGE].astype("string").fillna("Unknown")
    frequencies=timing.dropna().value_counts().sort_index()
    ecdf=[]
    cumulative=0
    for day,count in frequencies.items():
        cumulative+=int(count)
        ecdf.append({"days":float(day),"fraction":cumulative/int(frequencies.sum())})
    return {"age":age,"sex":sex,"grade":grade,"stage":stage,"n":len(selected),"followup_valid":len(valid),"timing_unknown":int(timing.isna().sum()-selected.timing_capped.sum()),"timing_capped":int(selected.timing_capped.sum()),"timing_stats":stats(timing),"timing_histogram":histogram(timing,[0,1,8,15,31,61,91,181,366,731]),"timing_ecdf":ecdf,"followup_stats":stats(valid.months),"followup_histogram":histogram(valid.months,[0,1,6,12,24,36,60,120,240,600]),"age_distribution":categories(age_labels),"sex_distribution":categories(selected.sex),"grade_distribution":categories(selected.grade),"stage_distribution":categories(selected.stage),"surgery_distribution":categories(selected.surgery),"chemotherapy_distribution":categories(selected.chemotherapy),"radiation_distribution":categories(selected.radiation),"subtype_distribution":categories(selected.subtype),"survival_curve":curves}


def fixture(cohort,n=700):
    rng=np.random.default_rng(20261014+list(ARCHIVES).index(cohort))
    age=rng.choice(["25-29 years","40-44 years","55-59 years","65-69 years","75-79 years"],n)
    grade=rng.choice(["Grade I; well differentiated","Grade II; moderately differentiated","Grade III; poorly differentiated","Unknown"],n)
    sex=np.repeat("Male",n) if cohort=="Prostate" else rng.choice(["Female","Male"],n,p=[.9,.1] if cohort=="Breast" else [.5,.5])
    years=rng.integers(2010,2018,n)
    hazard=(.035 if cohort=="Brain" else .007)*np.where(np.char.startswith(age,"75"),1.7,1)*np.where(np.char.startswith(grade,"Grade III"),1.9,1)
    failure=rng.exponential(1/hazard)
    censor=rng.uniform(24,150,n)
    months=np.floor(np.minimum(failure,censor)).astype(int)
    liver_stage=rng.choice(["Localized","Regional","Distant","Unknown / unavailable"],n) if cohort=="Liver" else np.repeat("Unknown / unavailable",n)
    values={ID:[f"invented-{cohort}-{i}" for i in range(n)],YEAR:years.astype(str),AGE:age,SEX:sex,GRADE:grade,INCOME:rng.choice(["< $35,000","$55,000 - $59,999","$100,000 - $109,999"],n),TIME:months.astype(str),VITAL:np.where(failure<=censor,"Dead","Alive"),TIMING:rng.choice(["000","007","021","045","090","180","731+ days","Unable to calculate"],n),SURGERY:rng.choice(["00","20","40","99"],n),CHEMO:rng.choice(["Yes","No/Unknown"],n),RADIATION:rng.choice(["Beam radiation","None/Unknown"],n)}
    if cohort=="Liver": values[STAGE_FIELDS[0]]=liver_stage
    return pd.DataFrame(values).astype("string")


def build(folder,output,zip_path=None,synthetic=False):
    from patient_survival import train
    output.mkdir(parents=True,exist_ok=True)
    studies=[]
    for cohort in ARCHIVES:
        print(f"Reading {cohort} study",flush=True)
        raw,source=(fixture(cohort),{"archive":"Invented fixture","member":"None","source_rows":700,"columns":FIELDS+[STAGE_FIELDS[0]] if cohort=="Liver" else FIELDS,"stage_columns":[STAGE_FIELDS[0]] if cohort=="Liver" else [],"matches_zip_raw_extract":None}) if synthetic else read_archive(folder,cohort,zip_path)
        frame=normalize(raw)
        missing_ids=len(raw)-int(raw[ID].notna().sum())
        source.update({"index_patients":len(frame),"missing_ids":missing_ids,"repeated_records_removed":len(raw)-missing_ids-len(frame)})
        # EDA population: all earliest-index patients in the supplied extract.
        views=[]
        stages=sorted(frame.stage.unique())
        for age in ["All",*sorted(frame.age_band.unique())]:
            for sex in ["All",*sorted(frame.sex.unique())]:
                for grade in ["All",*sorted(frame.grade.unique())]:
                    for stage in ["All",*stages]: views.append(profile(frame,age,sex,grade,stage))
        model=train(frame,cohort,output/"models",synthetic)
        from treatment_assignment import train_assignment
        treatment=train_assignment(frame,cohort,output/"models",synthetic)
        stage_filters=[value for value in stages if value!="Unknown / unavailable"] if source["stage_columns"] else []
        study={"cohort":cohort,"synthetic":synthetic,"source":source,"age_filters":sorted(frame.age_band.unique()),"sex_filters":sorted(frame.sex.unique()),"grade_filters":sorted(frame.grade.unique()),"stage_filters":stage_filters,"profiles":views,"model":model,"treatment_assignment":treatment,"notes":["Cancer-patient records, not a survivor-only cohort.","No cross-cancer pooling or cross-archive linkage.","Stage is sourced only where an explicit stage field exists; grade is not a stage proxy.","Treatment model predicts source-recorded surgery assignment; it cannot identify treatment benefit or recommend care.","EDA and temporal model populations are distinct.","Surgery, radiation and chemotherapy patterns are descriptive; no treatment is recommended.","Timing is first-course management, not a modality-specific delay."]}
        (output/f"{cohort.lower()}.json").write_text(json.dumps(study,ensure_ascii=False,allow_nan=False),encoding="utf-8")
        studies.append({"cohort":cohort,"file":cohort.lower()+".json","stage_available":bool(source["stage_columns"])})
        del raw,frame
        print(f"Completed {cohort} dashboard and temporal survival model",flush=True)
    (output/"catalog.json").write_text(json.dumps({"synthetic":synthetic,"classification":"SYNTHETIC DEMONSTRATION" if synthetic else "CONFIDENTIAL LOCAL RESEARCH","studies":studies},indent=2),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path)
    parser.add_argument("--zip",type=Path)
    parser.add_argument("--output",type=Path,default=Path(".runtime/patient-studies"))
    parser.add_argument("--synthetic",action="store_true")
    args=parser.parse_args()
    if not args.synthetic and args.folder is None: parser.error("--folder is required for confidential source archives")
    build(args.folder,args.output,args.zip,args.synthetic)
