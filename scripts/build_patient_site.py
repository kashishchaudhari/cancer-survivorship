"""Package only aggregate study JSON and frontend code; exclude trained models."""
import argparse
import json
import os
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
from patient_studies import ARCHIVES


def build(source,target):
    catalog=json.loads((source/"catalog.json").read_text())
    if os.environ.get("GITHUB_ACTIONS")=="true" and not catalog["synthetic"]:
        raise ValueError("Hosted CI may only use invented fixtures")
    names={"index.html","atlas.css","atlas.js","data/catalog.json"}|{f"data/{study['file']}" for study in catalog["studies"]}
    if target.exists() and any(path.is_file() and path.relative_to(target).as_posix() not in names for path in target.rglob("*")):
        raise ValueError("Build target contains non-allowlisted files; use a new directory")
    for study in catalog["studies"]:
        if study["file"]!=study["cohort"].lower()+".json" or study["cohort"] not in ARCHIVES: raise ValueError("Unexpected study path")
        data=json.loads((source/study["file"]).read_text())
        if data["cohort"]!=study["cohort"] or data["synthetic"]!=catalog["synthetic"]: raise ValueError("Study population / confidentiality mismatch")
        for profile in data["profiles"]:
            if not profile.get("suppressed"):
                assert profile["n"]>=11
                assert profile["timing_unknown"]>=0
                assert all(0<=point["low"]<=point["survival"]<=point["high"]<=1 for point in profile["survival_curve"])
                assert all(point["at_risk"]>=11 for point in profile["survival_curve"])
    target.mkdir(parents=True,exist_ok=True); (target/"data").mkdir(exist_ok=True)
    for asset in ["index.html","atlas.css","atlas.js"]: shutil.copyfile(ROOT/"patient_dashboard"/asset,target/asset)
    for file in ["catalog.json",*[study["file"] for study in catalog["studies"]]]: shutil.copyfile(source/file,target/"data"/file)
    print(f"Packaged {len(catalog['studies'])} independent studies; trained models are outside the web root.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=Path(".runtime/patient-studies"))
    parser.add_argument("--target",type=Path,default=Path(".runtime/patient-site"))
    args=parser.parse_args(); build(args.source,args.target)
