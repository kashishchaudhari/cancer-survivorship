"""Build a public explorer exclusively from the already-published research tables."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

COHORTS = ("Brain", "Breast", "Prostate", "Skin", "Liver")


def table_rows(text):
    return [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in text.splitlines() if line.startswith("| ")]


def number(value):
    return float(value.replace(",", "").rstrip("%"))


def extract(docs: Path):
    summary = (docs / "RESULTS_SUMMARY.md").read_text(encoding="utf-8")
    cases = (docs / "CASE_STUDIES.md").read_text(encoding="utf-8")
    summary_rows = table_rows(summary)
    case_rows = table_rows(cases)
    studies = []
    for cohort in COHORTS:
        primary = [r for r in summary_rows if r[0] == cohort and len(r) == 6]
        descriptive = [r for r in summary_rows if r[0] == cohort and len(r) == 10]
        interval = [r for r in case_rows if r[0].startswith(f"[{cohort}](")]
        if len(primary) != 1 or len(descriptive) != 1 or len(interval) != 1:
            raise ValueError(f"Expected one published row per table for {cohort}")
        p, d, c = primary[0], descriptive[0], interval[0]
        match = re.fullmatch(r"([\d.]+) \(([\d.]+)[–-]([\d.]+)\)", c[2])
        if not match:
            raise ValueError("Published AUC interval format changed")
        auc, low, high = map(float, match.groups())
        if (auc != number(p[4]) or number(c[1]) != number(p[1])
                or number(c[3]) != number(p[3]) or number(c[4]) != number(p[2])):
            raise ValueError("Published reports disagree")
        if not 0 <= low <= auc <= high <= 1:
            raise ValueError("Invalid published interval")
        q1, q3 = map(float, re.split("[–-]", d[4]))
        studies.append({
            "cohort": cohort, "source_rows": int(number(d[1])),
            "index_patients": int(number(d[2])), "median_days": number(d[3]),
            "timing_iqr": [q1, q3], "timing_sd": number(d[5]),
            "unknown_timing_pct": number(d[6]), "stage_available": cohort == "Liver",
            "primary": {"test_n": int(number(p[1])), "prevalence": number(p[2]),
                        "ap": number(p[3]), "auc": auc, "auc_ci": [low, high], "brier": number(p[5])},
            "temporal": {"test_n": int(number(d[9])), "auc": number(d[7]), "brier": number(d[8])},
        })
    return {"classification": "PUBLISHED REAL-DATA AGGREGATES", "synthetic": False,
            "scope": "Internal evaluation of supplied sampled datasets; not validated clinical or population risk estimates.",
            "sources": [{"path": name, "sha256": hashlib.sha256((docs / name).read_bytes()).hexdigest()}
                        for name in ("RESULTS_SUMMARY.md", "CASE_STUDIES.md")],
            "studies": studies}


def build(docs: Path, template: Path, output: Path):
    payload = extract(docs)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "research.js", "research.css"):
        shutil.copyfile(template / name, output / name)
    (output / "research-results.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    print("Built five research studies from two public Markdown reports; no private files read.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--template", type=Path, default=Path("research_dashboard"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.docs, args.template, args.output)
