"""Render confidential validation evidence as a readable local Markdown report."""
import json
from pathlib import Path


def render(source: Path, output: Path):
    evidence = json.loads(source.read_text(encoding="utf-8"))
    if evidence["status"] != "passed":
        raise ValueError("Cannot report a successful validation from incomplete evidence")
    lines = ["# Confidential data and reliability assessment", "", "Local research only. No permission for publication or cloud upload is implied.", "", "## Verdict", "", "The raw descriptive counts and defined care-survival calculations reconcile with independent reconstructions from the complete supplied archive. Clinical prediction reliability, population representativeness and causal treatment effects remain unestablished. Software tests are not a substitute for those study requirements.", "", "## Exact source", "", f"Original archive: `{evidence['archive']}`", "", f"Archive SHA-256: `{evidence['archive_sha256']}`", "", "The raw modules use the five text extracts in this archive. They do not use only the stratified Excel workbooks. Original workbook suicide-survival charts remain a different, sampled analysis. The complete supplied archive is not verified as the complete SEER registry.", "", "| Extract | Valid-ID records | Unique patients within extract | Index patients, 2004–2022 | Diagnosis years | Cause of death field |", "| --- | ---: | ---: | ---: | --- | --- |"]
    for member in evidence["members"]:
        lines.append(f"| {member['cohort']} | {member['valid_id_records']:,} | {member['unique_patients_in_extract']:,} | {member['period_index_patients']:,} | {member['year_min']}–{member['year_max']} | {'Present' if member['cause_of_death_present'] else 'Absent'} |")
    lines += ["", "Unique counts within individual extracts are not additive because patients can occur in more than one extract. The care module selects earliest diagnoses before its period restriction; it does not reuse later records to re-enter the period.", "", "Additional archive members:", ""]
    lines.extend(f"- `{name}`" for name in evidence["additional_archive_members"])
    lines += ["", "## Independent checks", "", "| Check | Status | Evidence |", "| --- | --- | --- |"]
    for check in evidence["checks"]:
        details = ", ".join(f"{key}: {value}" for key,value in check.items() if key not in {"check","status"})
        lines.append(f"| {check['check']} | {check['status']} | {details} |")
    lines += ["", "The KM product-limit estimator, log-log Greenwood confidence intervals and at-risk counts are calculated separately from the dashboard ETL. Tests include tied events/censoring, zero-month events, no events and complete failure. This verifies the care-view estimates; it does not independently validate the older sampled-workbook survival curves or refit the machine-learning models.", "", "## Missingness is not uniform", "", "| Dimension | Group | Patients | Timing recorded | Follow-up usable |", "| --- | --- | ---: | ---: | ---: |"]
    for group in evidence["care_missingness_by_group"]:
        n = group["patients"]
        lines.append(f"| {group['dimension']} | {group['category']} | {n:,} | {100*group['timing_known']/n:.1f}% | {100*group['followup_usable']/n:.1f}% |")
    lines += ["", "Differences in recorded timing may partly reflect data availability and selection. Unadjusted charts cannot isolate access barriers or treatment effects. Area income is contextual, not an individual's income.", "", "## Follow-up and zero-month sensitivity", "", f"Usable zero-month follow-up records in the selected care cohort: {evidence['zero_month_followup']:,}.", "", "| Horizon | Primary all-cause KM survival | Excluding zero-month records | At risk | Censored before horizon |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in evidence["care_followup_sensitivity"]:
        lines.append(f"| {row['months']} months | {100*row['primary_survival']:.2f}% | {100*row['excluding_zero_month_survival']:.2f}% | {row['patients_at_risk']:,} | {row['censored_before_horizon']:,} |")
    lines += ["", "Excluding zero-month records changes the cohort and produces different estimates. These sensitivity values do not justify choosing the more favorable result. Primary estimates retain zero-month follow-up. Censoring and source selection still limit interpretation.", "", "## Prediction limits and next study requirements", "", "The model test fold has been reused to compare configurations. This validation does not establish an untouched model evaluation, fixed-horizon personal risk, external calibration, subgroup clinical usefulness or treatment optimization. Future work needs a defined prediction time and endpoint, development-only selection, an untouched evaluation, calibration and uncertainty, and source-owner confirmation of sampling and follow-up.", "", "Original registry coverage, extraction filters, submission version, follow-up cutoff and common patient-ID namespace remain provenance questions. Permission to disclose any actual findings must be documented before external sharing.", "", "## Confidentiality changes", "", "Current Git tracking excludes derived outputs and reports; local originals are preserved. Real-data Pages deployment and artifact uploads are disabled. GitHub tests use invented fixtures. The old local commit still contains results, so do not push the existing Git history. A fresh code-only export is prepared separately, without .git or data directories.", ""]
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text("\n".join(lines),encoding="utf-8")


if __name__ == "__main__":
    render(Path(".runtime/validation/source_validation.json"),Path(".runtime/validation/REPORT.md"))
    print("Wrote confidential local reliability report.")
