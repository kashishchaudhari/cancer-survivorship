"""Build an editable PBIP/PBIR Atlas; public builds contain invented aggregates only."""
import argparse
import json
import math
import tempfile
from pathlib import Path

from patient_studies import ARCHIVES, fixture, normalize, profile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
COLORS = {"paper": "#F2F0E9", "panel": "#FFFEFA", "ink": "#17363D", "green": "#147D70", "amber": "#B88443"}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def synthetic_studies():
    from patient_survival import train
    from treatment_assignment import train_assignment
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    studies = []
    with tempfile.TemporaryDirectory(dir=runtime, prefix="powerbi-fixtures-") as temporary:
        for cohort in ARCHIVES:
            print(f"Power BI invented fixture: {cohort}", flush=True)
            frame = normalize(fixture(cohort, n=2000))
            survival = train(frame, cohort, temporary, synthetic=True, save_artifact=False)
            survival["temporal_sensitivity"] = train(frame, cohort, temporary, synthetic=True,
                                                     strategy="temporal", save_artifact=False)
            surgery = train_assignment(frame, cohort, temporary, synthetic=True)
            surgery["temporal_sensitivity"] = train_assignment(frame, cohort, temporary, synthetic=True, strategy="temporal")
            studies.append({"cohort": cohort, "synthetic": True,
                            "source": {"source_rows": len(frame), "index_patients": len(frame),
                                       "stage_columns": ["Invented explicit summary stage"] if cohort == "Liver" else []},
                            "profiles": [profile(frame)], "model": survival, "treatment_assignment": surgery})
    return studies


def collect_tables(studies):
    """Explicit aggregate field allowlist; source rows and identifiers never enter the model."""
    if {s["cohort"] for s in studies} != set(ARCHIVES) or len(studies) != 5:
        raise ValueError("Exactly five independent cancer studies are required")
    result = {name: [] for name in ["Cohorts", "Strategies", "Horizons", "Modalities", "SurgeryEvaluation",
                                   "SurgeryCalibration", "SurvivalEvaluation", "TreatmentPatterns"]}
    result["Strategies"] = [["Patient holdout", 1], ["Temporal sensitivity", 2]]
    result["Horizons"] = [[12, "1 year"], [36, "3 years"], [60, "5 years"]]
    result["Modalities"] = [["Surgery"], ["Radiation"], ["Chemotherapy"]]
    for order, cohort in enumerate(ARCHIVES, 1):
        study = next(s for s in studies if s["cohort"] == cohort)
        surgery, survival = study["treatment_assignment"], study["model"]
        if surgery.get("strategy") != "patient" or survival.get("strategy") != "patient":
            raise ValueError("Requires refreshed patient-holdout evaluations")
        whole = next(p for p in study["profiles"] if all(p[key] == "All" for key in ["age", "sex", "grade", "stage"]))
        stats = whole["timing_stats"]
        result["Cohorts"].append([cohort, order, study["source"]["source_rows"],
                                  study["source"]["index_patients"],
                                  "Available: source summary stage" if study["source"]["stage_columns"] else "Unavailable in source",
                                  stats.get("median"), whole["timing_unknown"], whole["timing_capped"]])
        for field, modality in [("surgery_distribution", "Surgery"), ("radiation_distribution", "Radiation"),
                                ("chemotherapy_distribution", "Chemotherapy")]:
            for row in whole[field]:
                result["TreatmentPatterns"].append([cohort, modality, row["label"], row["count"], row["status"], whole["n"]])
        for label, sm, vm in [("Patient holdout", surgery, survival),
                              ("Temporal sensitivity", surgery["temporal_sensitivity"], survival["temporal_sensitivity"])]:
            test = sm["test"]
            development = sm["splits"]["development"]
            training_n, training_positive = development["patients"], development["surgery_recorded"]
            if "validation" in sm["splits"]:
                training_n += sm["splits"]["validation"]["patients"]
                training_positive += sm["splits"]["validation"]["surgery_recorded"]
            q = training_positive / training_n
            p = test["prevalence"]
            baseline = p * (1-q)**2 + (1-p) * q**2
            result["SurgeryEvaluation"].append([cohort, label, test["patients"], test["positive"], p,
                                                test["average_precision"], test["roc_auc"], test["brier"], baseline])
            for index, row in enumerate(sm["calibration"], 1):
                result["SurgeryCalibration"].append([cohort, label, str(index), row["predicted"], row["observed"], row["n"]])
            for row in vm["evaluation"]["metrics"]:
                result["SurvivalEvaluation"].append([cohort, label, row["months"], vm["splits"]["test"]["patients"],
                                                      vm["evaluation"]["c_index"], row["ipcw_brier"], row["baseline_brier"],
                                                      row["at_risk"], row["support"]])
    return result


TABLE_COLUMNS = {
    "Cohorts": [("Cohort", "string"), ("SortOrder", "int64"), ("SourceRecords", "int64"), ("IndexPatients", "int64"),
                ("StageAvailability", "string"), ("MedianTimingDays", "double"), ("TimingUnknown", "int64"), ("TimingTopCoded", "int64")],
    "Strategies": [("Strategy", "string"), ("SortOrder", "int64")],
    "Horizons": [("Months", "int64"), ("Horizon", "string")],
    "Modalities": [("Modality", "string")],
    "SurgeryEvaluation": [("Cohort", "string"), ("Strategy", "string"), ("TestPatients", "int64"), ("SurgeryRecorded", "int64"),
                          ("Prevalence", "double"), ("AveragePrecision", "double"), ("RocAuc", "double"), ("Brier", "double"), ("BaselineBrier", "double")],
    "SurgeryCalibration": [("Cohort", "string"), ("Strategy", "string"), ("Bin", "string"),
                           ("Predicted", "double"), ("Observed", "double"), ("GroupPatients", "int64")],
    "SurvivalEvaluation": [("Cohort", "string"), ("Strategy", "string"), ("Months", "int64"), ("TestPatients", "int64"),
                           ("CIndex", "double"), ("IpcwBrier", "double"), ("BaselineBrier", "double"), ("AtRisk", "int64"), ("Support", "string")],
    "TreatmentPatterns": [("Cohort", "string"), ("Modality", "string"), ("Category", "string"),
                          ("PatientCount", "int64"), ("Status", "string"), ("Denominator", "int64")],
}


def m_literal(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return '"' + value.replace("#", "#(#)").replace('"', '""').replace("\n", "#(lf)").replace("\r", "#(cr)") + '"'
    if isinstance(value, (float, int)) and not math.isfinite(value):
        raise ValueError("Nonfinite aggregate value")
    return str(value)


def model_definition(tables, synthetic):
    mtypes = {"string": "text", "int64": "Int64.Type", "double": "number"}
    model_tables = []
    for name, columns in TABLE_COLUMNS.items():
        declaration = ", ".join(f"{column} = {mtypes[kind]}" for column, kind in columns)
        rows = ",\n".join("{" + ", ".join(m_literal(value) for value in row) + "}" for row in tables[name])
        expression = f"#table(type table [{declaration}], {{\n{rows}\n}})"
        specs = [{"name": column, "dataType": kind, "sourceColumn": column, "summarizeBy": "none"} for column, kind in columns]
        if name == "Cohorts": specs[0]["sortByColumn"] = "SortOrder"
        if name == "Strategies": specs[0]["sortByColumn"] = "SortOrder"
        if name == "Horizons": specs[1]["sortByColumn"] = "Months"
        model_tables.append({"name": name, "columns": specs, "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": expression}}]})
    choice = 'COALESCE(SELECTEDVALUE(Strategies[Strategy]), "Patient holdout")'
    measures = []
    for display, table, column, fmt in [
        ("Surgery test patients", "SurgeryEvaluation", "TestPatients", "#,0"),
        ("Surgery recorded", "SurgeryEvaluation", "SurgeryRecorded", "#,0"),
        ("Surgery prevalence", "SurgeryEvaluation", "Prevalence", "0.0%"),
        ("Surgery average precision", "SurgeryEvaluation", "AveragePrecision", "0.000"),
        ("Surgery ROC AUC", "SurgeryEvaluation", "RocAuc", "0.000"),
        ("Surgery Brier", "SurgeryEvaluation", "Brier", "0.000"),
        ("Surgery baseline Brier", "SurgeryEvaluation", "BaselineBrier", "0.000"),
        ("Predicted surgery probability", "SurgeryCalibration", "Predicted", "0.0%"),
        ("Observed surgery fraction", "SurgeryCalibration", "Observed", "0.0%"),
        ("Calibration group patients", "SurgeryCalibration", "GroupPatients", "#,0"),
        ("Survival C-index", "SurvivalEvaluation", "CIndex", "0.000"),
        ("Cox IPCW Brier", "SurvivalEvaluation", "IpcwBrier", "0.000"),
        ("KM baseline Brier", "SurvivalEvaluation", "BaselineBrier", "0.000"),
        ("Survival test patients", "SurvivalEvaluation", "TestPatients", "#,0"),
        ("Patients at risk", "SurvivalEvaluation", "AtRisk", "#,0"),
    ]:
        dax = f'VAR ChosenStrategy = {choice}\nRETURN IF(HASONEVALUE(Cohorts[Cohort]), CALCULATE(SELECTEDVALUE({table}[{column}]), {table}[Strategy] = ChosenStrategy), BLANK())'
        measures.append({"name": display, "expression": dax, "formatString": fmt})
    for display, column, fmt in [("Index patients", "IndexPatients", "#,0"), ("Source records", "SourceRecords", "#,0"),
                                 ("Median timing days", "MedianTimingDays", "0.0"), ("Stage availability", "StageAvailability", "")]:
        measures.append({"name": display, "expression": f"IF(HASONEVALUE(Cohorts[Cohort]), SELECTEDVALUE(Cohorts[{column}]), BLANK())", "formatString": fmt})
    next(m for m in measures if m["name"] == "Stage availability")["expression"] = 'IF(HASONEVALUE(Cohorts[Cohort]), IF(SELECTEDVALUE(Cohorts[StageAvailability]) = "Available: source summary stage", "Available", "Unavailable"), BLANK())'
    measures += [{"name": "Recorded treatment patients", "expression": "IF(HASONEVALUE(Cohorts[Cohort]) && HASONEVALUE(Modalities[Modality]), SUM(TreatmentPatterns[PatientCount]), BLANK())", "formatString": "#,0"},
                 {"name": "AP lift over prevalence", "expression": "DIVIDE([Surgery average precision], [Surgery prevalence])", "formatString": "0.00x"},
                 {"name": "Selected study", "expression": 'SELECTEDVALUE(Cohorts[Cohort], "Choose one cancer")'},
                 {"name": "Selected evaluation", "expression": choice},
                 {"name": "Data classification", "expression": '"SYNTHETIC DEMONSTRATION - invented values"' if synthetic else '"CONFIDENTIAL LOCAL AGGREGATES"'}]
    model_tables[0]["measures"] = measures
    relationships = []
    for table in ["SurgeryEvaluation", "SurgeryCalibration", "SurvivalEvaluation", "TreatmentPatterns"]:
        relationships.append({"name": "Cohort_" + table, "fromTable": table, "fromColumn": "Cohort", "toTable": "Cohorts", "toColumn": "Cohort", "crossFilteringBehavior": "oneDirection"})
        if table != "TreatmentPatterns":
            relationships.append({"name": "Strategy_" + table, "fromTable": table, "fromColumn": "Strategy", "toTable": "Strategies", "toColumn": "Strategy", "crossFilteringBehavior": "oneDirection"})
    relationships.append({"name": "Modality_Treatments", "fromTable": "TreatmentPatterns", "fromColumn": "Modality", "toTable": "Modalities", "toColumn": "Modality", "crossFilteringBehavior": "oneDirection"})
    relationships.append({"name": "Horizon_Survival", "fromTable": "SurvivalEvaluation", "fromColumn": "Months", "toTable": "Horizons", "toColumn": "Months", "crossFilteringBehavior": "oneDirection"})
    return {"name": "CancerPatientAtlas", "compatibilityLevel": 1601,
            "model": {"culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "tables": model_tables,
                      "relationships": relationships,
                      "annotations": [{"name": "AtlasDataClassification", "value": "SYNTHETIC" if synthetic else "CONFIDENTIAL_LOCAL"}]}}


def literal(value):
    encoded = "true" if value is True else "false" if value is False else str(value) if isinstance(value, (float, int)) else "'" + value.replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": encoded}}}


def fill(color):
    return {"solid": {"color": literal(color)}}


def projection(table, field, measure=False):
    kind = "Measure" if measure else "Column"
    return {"field": {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": field}},
            "queryRef": f"{table}.{field}", "nativeQueryRef": field}


def visual(name, visual_type, title, box, roles=None, text=None, sync=None):
    x, y, width, height = box
    config = {"visualType": visual_type, "visualContainerObjects": {
        "title": [{"properties": {"show": literal(bool(title)), "text": literal(title), "fontSize": literal(12), "fontColor": fill(COLORS["ink"])}}],
        "background": [{"properties": {"show": literal(True), "color": fill(COLORS["panel"]), "transparency": literal(0)}}]}}
    if roles:
        config["query"] = {"queryState": {role: {"projections": fields} for role, fields in roles.items()}}
    if text is not None:
        config["objects"] = {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": {"fontFamily": "Segoe UI", "fontSize": "14pt", "color": COLORS["ink"]}}]}]}}]}
    if sync:
        config["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
        config["objects"] = {"selection": [{"properties": {"singleSelect": literal(True)}}]}
    return {"$schema": SCHEMA + "item/report/definition/visualContainer/2.9.0/schema.json", "name": name,
            "position": {"x": x, "y": y, "width": width, "height": height, "z": 0, "tabOrder": 0}, "visual": config}


def report_pages(synthetic):
    col = lambda table, field: projection(table, field)
    measure = lambda name: projection("Cohorts", name, True)
    pages = []
    specs = [
        ("overview", "01 · Study overview", "Five cancer studies, kept independent", "Choose one cancer for KPI cards. All-cancer charts retain separate denominators."),
        ("care", "02 · Recorded care", "Inspect what was recorded", "No/unknown does not mean confirmed non-treatment. Suppressed counts remain missing."),
        ("surgery", "03 · Surgery evaluation", "Compare prediction with its baseline", "Target: known surgery codes 00 versus 01–90. This does not estimate treatment benefit."),
        ("calibration", "04 · Calibration", "Do probabilities match recorded frequencies?", "Choose one cancer. Each point is an aggregate probability bin, not a patient."),
        ("survival", "05 · Survival evaluation", "Test all-cause survival against a cohort baseline", "Choose one cancer. Unsupported horizons remain blank; censoring and follow-up still matter."),
        ("comparison", "06 · Evaluation comparison", "Patient holdout and temporal sensitivity", "Different, overlapping populations. Score differences do not establish improvement caused by resplitting."),
        ("methods", "07 · Methods and scope", "Make the study design inspectable", "Internal research evaluation; no clinical or population risk claims."),
    ]
    banner = "SYNTHETIC DEMONSTRATION · INVENTED VALUES · NO CLINICAL MEANING" if synthetic else "CONFIDENTIAL LOCAL RESEARCH · INTERNAL EVALUATION ONLY"
    for page_name, display_name, headline, subtitle in specs:
        items = [visual("header", "textbox", "", (24, 16, 1232, 42), text=headline),
                 visual("scope", "textbox", "", (24, 62, 1232, 46), text=banner + "\n" + subtitle),
                 visual("cohort_slicer", "slicer", "Cancer study", (24, 118, 500, 76), {"Values": [col("Cohorts", "Cohort")]}, sync="CancerSelection"),
                 visual("strategy_slicer", "slicer", "Evaluation design (default: patient holdout)", (548, 118, 708, 76), {"Values": [col("Strategies", "Strategy")]}, sync="EvaluationSelection")]
        if page_name == "overview":
            for index, name in enumerate(["Index patients", "Source records", "Median timing days", "Stage availability"]):
                items.append(visual(f"kpi_{index}", "card", name, (24+index*312, 214, 288, 102), {"Values": [measure(name)]}))
            items.append(visual("cohort_table", "tableEx", "Separate source populations", (24, 338, 1232, 306), {"Values": [col("Cohorts", "Cohort"), measure("Index patients"), measure("Source records"), measure("Stage availability")]}))
        elif page_name == "care":
            items.append(visual("modality", "slicer", "Recorded modality", (24, 214, 270, 90), {"Values": [col("Modalities", "Modality")]}))
            items.append(visual("counts", "barChart", "Recorded categories (choose a cancer and modality)", (318, 214, 938, 430), {"Category": [col("TreatmentPatterns", "Category")], "Y": [measure("Recorded treatment patients")]}))
        elif page_name == "surgery":
            for index, name in enumerate(["Surgery test patients", "Surgery ROC AUC", "Surgery Brier", "AP lift over prevalence"]):
                items.append(visual(f"kpi_{index}", "card", name, (24+index*312, 214, 288, 102), {"Values": [measure(name)]}))
            items.append(visual("ap", "clusteredColumnChart", "Average precision versus prevalence", (24, 338, 604, 306), {"Category": [col("Cohorts", "Cohort")], "Y": [measure("Surgery average precision"), measure("Surgery prevalence")]}))
            items.append(visual("brier", "clusteredColumnChart", "Brier versus development-prevalence baseline", (652, 338, 604, 306), {"Category": [col("Cohorts", "Cohort")], "Y": [measure("Surgery Brier"), measure("Surgery baseline Brier")]}))
        elif page_name == "calibration":
            items.append(visual("scatter", "scatterChart", "Predicted versus observed surgery recording", (24, 214, 784, 430), {"Category": [col("SurgeryCalibration", "Bin")], "X": [measure("Predicted surgery probability")], "Y": [measure("Observed surgery fraction")], "Size": [measure("Calibration group patients")]}))
            items.append(visual("bins", "tableEx", "Aggregate calibration groups", (832, 214, 424, 430), {"Values": [col("SurgeryCalibration", "Bin"), measure("Predicted surgery probability"), measure("Observed surgery fraction"), measure("Calibration group patients")]}))
        elif page_name == "survival":
            items.append(visual("horizon", "slicer", "Prediction horizon", (24, 214, 270, 90), {"Values": [col("Horizons", "Horizon")]}))
            items.append(visual("cindex", "card", "All-cause test C-index", (24, 326, 270, 120), {"Values": [measure("Survival C-index")]}))
            items.append(visual("brier", "clusteredColumnChart", "Censoring-adjusted prediction error", (318, 214, 938, 288), {"Category": [col("Horizons", "Horizon")], "Y": [measure("Cox IPCW Brier"), measure("KM baseline Brier")]}))
            items.append(visual("risk", "tableEx", "Horizon support and test population", (318, 524, 938, 120), {"Values": [col("Horizons", "Horizon"), measure("Survival test patients"), measure("Patients at risk"), measure("Cox IPCW Brier")]}))
        elif page_name == "comparison":
            items.append(visual("comparison_table", "tableEx", "Each cohort and evaluation retains its own test population", (24, 214, 1232, 430), {"Values": [col("Cohorts", "Cohort"), col("Strategies", "Strategy"), measure("Surgery test patients"), measure("Surgery ROC AUC"), measure("Surgery average precision"), measure("Surgery prevalence"), measure("Surgery Brier"), measure("Survival C-index")]}))
        else:
            text = ("PRIMARY: stratified 80/20 patient holdout; development-only cross-validation selects regularization. Preprocessing is fitted within each training fold.\n\n"
                    "SECONDARY: 2010–2013 development, 2014–2015 validation, 2016–2017 temporal test. Model eligibility remains 2010–2017 for the existing source era.\n\n"
                    "SOURCES: Brain, Breast, Prostate and Skin coursework extracts have no usable stage. Liver uses explicit source summary stage. Grade is not a stage proxy.\n\n"
                    "LIMITS: revised internal evaluation of the supplied sampled dataset. Prior results were inspected. No independent confirmatory validation, clinical risk estimate, treatment-effect claim, or individual recommendation is established.\n\n"
                    "DESIGN: ratios and discrimination measures are never averaged across cancer types. Select a cancer to inspect metrics; report pages keep descriptive and model populations separate.")
            items.append(visual("methods", "textbox", "", (24, 214, 1232, 430), text=text))
        items.append(visual("footer", "textbox", "", (24, 662, 1232, 40), text="Cancer Patient Atlas · aggregate-only report · research use · " + ("invented demo" if synthetic else "confidential local build")))
        pages.append((page_name, {"$schema": SCHEMA+"item/report/definition/page/2.0.0/schema.json", "name": page_name,
                                  "displayName": display_name, "displayOption": "FitToPage", "height": 720, "width": 1280,
                                  "objects": {"background": [{"properties": {"color": fill(COLORS["paper"]), "transparency": literal(0)}}]}}, items))
    return pages


def build(studies, output, synthetic):
    if any(s["synthetic"] != synthetic for s in studies):
        raise ValueError("Mixed or mislabeled source classification")
    if not synthetic and not output.resolve().is_relative_to((ROOT / ".runtime").resolve()):
        raise ValueError("Real-data Power BI builds must remain under ignored .runtime")
    tables = collect_tables(studies)
    write_project(tables, output, synthetic)


def write_project(tables, output, synthetic):
    tables.setdefault("Modalities", [["Surgery"], ["Radiation"], ["Chemotherapy"]])
    if not synthetic and not output.resolve().is_relative_to((ROOT / ".runtime").resolve()):
        raise ValueError("Real-data Power BI builds must remain under ignored .runtime")
    write_json(output / "aggregate-data.json", {"synthetic": synthetic, "tables": tables})
    report = output / "CancerPatientAtlas.Report"
    semantic = output / "CancerPatientAtlas.SemanticModel"
    write_json(output / "CancerPatientAtlas.pbip", {"$schema": SCHEMA+"pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                                  "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
    write_json(report / "definition.pbir", {"$schema": SCHEMA+"item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../"+semantic.name}}})
    write_json(semantic / "definition.pbism", {"$schema": SCHEMA+"item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "1.0"})
    write_json(semantic / "model.bim", model_definition(tables, synthetic))
    version = {"visual": "2.9.0", "report": "3.1.0", "page": "2.0.0"}
    write_json(report / "definition/version.json", {"$schema": SCHEMA+"item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write_json(report / "definition/report.json", {"$schema": SCHEMA+"item/report/definition/report/3.1.0/schema.json",
               "themeCollection": {"customTheme": {"name": "AtlasTheme", "reportVersionAtImport": version, "type": "RegisteredResources"}},
               "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "AtlasTheme", "path": "AtlasTheme.json", "type": "CustomTheme"}]}],
               "annotations": [{"name": "AtlasDataClassification", "value": "SYNTHETIC" if synthetic else "CONFIDENTIAL_LOCAL"}]})
    write_json(report / "StaticResources/RegisteredResources/AtlasTheme.json", {"name": "Patient Atlas", "dataColors": [COLORS["green"], COLORS["amber"], "#477A9C", "#925D66", "#72835C"], "background": COLORS["paper"], "foreground": COLORS["ink"], "tableAccent": COLORS["green"], "textClasses": {"label": {"fontFace": "Segoe UI"}, "title": {"fontFace": "Segoe UI"}}})
    pages = report_pages(synthetic)
    write_json(report / "definition/pages/pages.json", {"$schema": SCHEMA+"item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": [name for name, _, _ in pages], "activePageName": "overview"})
    for name, page, visuals in pages:
        write_json(report / f"definition/pages/{name}/page.json", page)
        for item in visuals:
            write_json(report / f"definition/pages/{name}/visuals/{item['name']}/visual.json", item)
    write_json(output / "build-manifest.json", {"synthetic": synthetic, "cohorts": list(ARCHIVES), "pages": len(pages),
                                               "table_rows": {name: len(rows) for name, rows in tables.items()},
                                               "data_grain": "Cohort aggregates and calibration bins; no patient rows", "refresh": "Embedded aggregate snapshot; regenerate to update source results"})
    print(f"Power BI project created: {len(pages)} pages, {len(tables)} aggregate tables; {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic", action="store_true")
    group.add_argument("--source", type=Path, help="Private refreshed patient-study JSON directory")
    parser.add_argument("--output", type=Path, default=ROOT / "powerbi/PatientAtlas")
    args = parser.parse_args()
    source = synthetic_studies() if args.synthetic else [json.loads((args.source / f"{n.lower()}.json").read_text(encoding="utf-8")) for n in ARCHIVES]
    build(source, args.output, args.synthetic)
