"""Temporally held-out all-cause survival research; no treatment recommendation."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.utils import concordance_index
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

HORIZONS=[12,36,60]


def encode_setup(categories):
    return ColumnTransformer([("numeric",SimpleImputer(strategy="median"),["age_mid"]),("category",OneHotEncoder(drop="first",handle_unknown="ignore",sparse_output=False),categories)],verbose_feature_names_out=True)


def design(encoder,frame,columns=None,fit=False):
    values=encoder.fit_transform(frame) if fit else encoder.transform(frame)
    result=pd.DataFrame(values,columns=encoder.get_feature_names_out())
    if columns is None: columns=result.columns[result.std().fillna(0)>1e-8].tolist()
    return result[columns],columns


def fit_model(frame,encoder,penalty,fit_encoder=True,columns=None):
    x,columns=design(encoder,frame,columns,fit_encoder)
    fitting=x.copy()
    fitting["duration"]=frame.model_months.to_numpy(dtype=float)
    fitting["death"]=frame.death.to_numpy(dtype=bool)
    model=CoxPHFitter(penalizer=penalty).fit(fitting,duration_col="duration",event_col="death")
    return model,columns


def c_index(model,x,frame):
    try: return float(concordance_index(frame.model_months,-model.predict_partial_hazard(x).to_numpy().ravel(),frame.death))
    except ZeroDivisionError: return None


def censor_weights(training,testing,horizon):
    km=KaplanMeierFitter().fit(training.model_months.astype(float),~training.death.astype(bool))
    times=km.survival_function_.index.to_numpy()
    values=km.survival_function_.iloc[:,0].to_numpy()
    positions=np.searchsorted(times,testing.model_months.to_numpy(),side="left")-1
    before=np.where(positions>=0,values[np.maximum(positions,0)],1.)
    g_h=float(km.predict(horizon))
    known_dead=testing.death.to_numpy() & testing.model_months.le(horizon).to_numpy()
    beyond=testing.model_months.gt(horizon).to_numpy()
    if g_h<.05 or int(beyond.sum())<11 or np.any(before[known_dead]<.05): return None
    weights=np.zeros(len(testing))
    weights[known_dead]=1/before[known_dead]
    weights[beyond]=1/g_h
    return weights,beyond.astype(float)


def evaluate(model,encoder,columns,training,testing):
    x,_=design(encoder,testing,columns)
    estimates=model.predict_survival_function(x,times=HORIZONS).to_numpy()
    baseline=KaplanMeierFitter().fit(training.model_months.astype(float),training.death.astype(bool))
    metrics=[]
    calibration=[]
    for index,horizon in enumerate(HORIZONS):
        weighted=censor_weights(training,testing,horizon)
        brier=baseline_brier=None
        if weighted is not None:
            weights,target=weighted
            brier=float(np.mean(weights*(target-estimates[index])**2))
            baseline_brier=float(np.mean(weights*(target-float(baseline.predict(horizon)))**2))
        metrics.append({"months":horizon,"ipcw_brier":brier,"baseline_brier":baseline_brier,"at_risk":int(testing.model_months.ge(horizon).sum()),"support":"Supported" if weighted is not None else "Insufficient censoring / at-risk support"})
        # Untouched-test calibration diagnostics, never used to refit or select.
        bins=pd.qcut(pd.Series(estimates[index]),q=5,duplicates="drop",labels=False)
        for group in sorted(bins.dropna().unique()):
            mask=bins.eq(group).to_numpy()
            part=testing.loc[mask]
            if len(part)<30 or int(part.model_months.ge(horizon).sum())<11: continue
            km=KaplanMeierFitter().fit(part.model_months.astype(float),part.death.astype(bool))
            ci=km.confidence_interval_.loc[km.confidence_interval_.index<=horizon].iloc[-1]
            calibration.append({"months":horizon,"predicted":float(estimates[index,mask].mean()),"observed":float(km.predict(horizon)),"low":float(ci.iloc[0]),"high":float(ci.iloc[1]),"n":len(part),"at_risk":int(part.model_months.ge(horizon).sum())})
    subgroup=[]
    for field in ["sex","age_band","grade"]:
        for label,part in testing.groupby(field):
            if len(part)<30 or int(part.death.sum())<5: continue
            xx,_=design(encoder,part,columns)
            subgroup.append({"dimension":field,"group":str(label),"n":len(part),"events":int(part.death.sum()),"c_index":c_index(model,xx,part)})
    return {"c_index":c_index(model,x,testing),"metrics":metrics,"calibration":calibration,"subgroups":subgroup}


def train(frame,cohort,model_dir,synthetic=False):
    eligible=frame.loc[frame.followup_valid & frame.year.between(2010,2017) & frame.age_mid.notna()].copy()
    development=eligible.loc[eligible.year.le(2013)]
    validation=eligible.loc[eligible.year.between(2014,2015)]
    test=eligible.loc[eligible.year.between(2016,2017)]
    counts={name:{"patients":len(part),"deaths":int(part.death.sum())} for name,part in [("development",development),("validation",validation),("test",test)]}
    if any(len(part)<50 or part.death.sum()<10 for part in [development,validation,test]):
        return {"status":"Not fitted: insufficient temporal split support","splits":counts}
    assert set(development["Patient ID"]).isdisjoint(set(test["Patient ID"]))
    assert set(validation["Patient ID"]).isdisjoint(set(test["Patient ID"]))
    categories=["sex","grade","income"]
    if eligible.stage.nunique()>1 and eligible.stage.ne("Unknown / unavailable").any(): categories.append("stage")
    if cohort=="Breast" and development.subtype.nunique()>1: categories.append("subtype")
    candidates=[]
    for penalty in [.01,.1,1.]:
        encoder=encode_setup(categories)
        model,columns=fit_model(development,encoder,penalty)
        x,_=design(encoder,validation,columns)
        score=c_index(model,x,validation)
        candidates.append({"penalty":penalty,"validation_c_index":score})
    selected=max(candidates,key=lambda row:row["validation_c_index"] if row["validation_c_index"] is not None else -1)
    training=pd.concat([development,validation],ignore_index=True)
    encoder=encode_setup(categories)
    model,columns=fit_model(training,encoder,selected["penalty"])
    evaluation=evaluate(model,encoder,columns,training,test)
    options={field:sorted(training[field].dropna().astype(str).unique()) for field in categories}
    ages=sorted(float(value) for value in training.age_mid.unique())
    model_dir=Path(model_dir); model_dir.mkdir(parents=True,exist_ok=True)
    # Model objects may contain training outcomes; keep these artifacts local.
    joblib.dump({"model":model,"encoder":encoder,"columns":columns,"categories":categories,"options":options,"ages":ages,"cohort":cohort,"synthetic":synthetic},model_dir/f"{cohort.lower()}.joblib")
    coefficients=[{"feature":str(feature),"hazard_ratio":float(np.exp(coef))} for feature,coef in model.params_.items()]
    return {"status":"Fitted / internal temporal evaluation","synthetic":synthetic,"endpoint":"All-cause survival","horizons":HORIZONS,"model":"Penalized Cox proportional hazards","splits":counts,"split_rule":"Index years 2010–2013 development; 2014–2015 validation; 2016–2017 untouched test. No patient overlap.","selected_penalty":selected["penalty"],"validation_candidates":candidates,"evaluation":evaluation,"coefficients":coefficients,"options":options,"ages":ages,"limitations":["Retrospective research features; their availability at a clinical decision time is not verified.","An explicit source stage field is included only where present; the four CancerProject archives do not contain one.","Treatment fields, follow-up duration, vital status and diagnosis year are excluded from predictors.","Source age bands use midpoint approximations; 85+ is represented by 87.5.","Zero-month follow-up uses 0.5 month for the positive-duration Cox model.","Proportional hazards, source representativeness and external calibration remain unvalidated.","Income is area context, not individual income.","No treatment benefit or patient treatment recommendation is estimated."]}


def predict(artifact,values):
    age=float(values.get("age_mid",-1))
    if age not in artifact["ages"]: raise ValueError("Select a supported source age-band midpoint")
    row={"age_mid":age}
    for field in artifact["categories"]:
        value=values.get(field)
        if value not in artifact["options"][field]: raise ValueError(f"Unsupported {field} category")
        row[field]=value
    x,_=design(artifact["encoder"],pd.DataFrame([row]),artifact["columns"])
    result=artifact["model"].predict_survival_function(x,times=HORIZONS).iloc[:,0]
    return {"cohort":artifact["cohort"],"synthetic":artifact["synthetic"],"endpoint":"All-cause survival","estimates":[{"months":int(month),"survival":float(probability)} for month,probability in result.items()],"interpretation":"Internal retrospective research-model estimates. Not externally validated clinical probabilities or treatment advice."}
