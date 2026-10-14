"""Refit both evaluations while preserving audited profiles; Cox objects are not saved."""
import argparse
import json
from pathlib import Path

from patient_studies import ARCHIVES, normalize, read_archive
from patient_survival import train
from treatment_assignment import train_assignment


def refresh(folder, archive, previous, output):
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((previous / "catalog.json").read_text(encoding="utf-8"))
    if catalog["synthetic"]:
        raise ValueError("Use the synthetic build for demonstration data")
    for cohort in ARCHIVES:
        existing = output / f"{cohort.lower()}.json"
        if existing.exists():
            completed = json.loads(existing.read_text(encoding="utf-8"))
            if completed["model"].get("strategy") != "patient" or completed["treatment_assignment"].get("strategy") != "patient":
                raise ValueError("Existing output uses a different evaluation design")
            print(f"Keeping completed {cohort}", flush=True)
            continue
        print(f"Refitting {cohort}", flush=True)
        raw, source = read_archive(folder, cohort, archive)
        study = json.loads((previous / f"{cohort.lower()}.json").read_text(encoding="utf-8"))
        if source["member_sha256"] != study["source"]["member_sha256"]:
            raise ValueError("Source changed; rebuild descriptive profiles")
        frame = normalize(raw)
        for key, fitter in [("model", train), ("treatment_assignment", train_assignment)]:
            options = {"save_artifact": False} if key == "model" else {}
            study[key] = fitter(frame, cohort, output / "models", **options)
            study[key]["temporal_sensitivity"] = fitter(frame, cohort, output / "models", strategy="temporal", **options)
        study["notes"] = [note.replace("EDA and temporal model populations", "EDA and model-eligible populations") for note in study["notes"]]
        (output / f"{cohort.lower()}.json").write_text(json.dumps(study, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        print(f"Completed {cohort}", flush=True)
    (output / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ["folder", "archive", "previous", "output"]:
        parser.add_argument(f"--{field}", type=Path, required=True)
    args = parser.parse_args()
    refresh(args.folder, args.archive, args.previous, args.output)
