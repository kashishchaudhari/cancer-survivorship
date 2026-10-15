"""Validate public Power BI metadata, field bindings and optional Microsoft JSON schemas."""
import argparse
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft7Validator
from referencing import Registry, Resource

from build_powerbi_atlas import TABLE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def inspect_project(project, public=True, schemas=False):
    manifest = json.loads((project / "build-manifest.json").read_text(encoding="utf-8"))
    data = json.loads((project / "aggregate-data.json").read_text(encoding="utf-8"))
    model = json.loads((project / "CancerPatientAtlas.SemanticModel/model.bim").read_text(encoding="utf-8"))
    if public and (manifest["synthetic"] is not True or data["synthetic"] is not True):
        raise ValueError("Public Power BI project must contain invented data only")
    classification = next(a["value"] for a in model["model"]["annotations"] if a["name"] == "AtlasDataClassification")
    if public and classification != "SYNTHETIC":
        raise ValueError("Semantic model is not marked synthetic")
    tables = {table["name"]: table for table in model["model"]["tables"]}
    if set(tables) != set(TABLE_COLUMNS) or set(data["tables"]) != set(TABLE_COLUMNS):
        raise ValueError("Unexpected Power BI tables")
    fields = {}
    for name, table in tables.items():
        expected = TABLE_COLUMNS[name]
        if [(c["name"], c["dataType"]) for c in table["columns"]] != expected:
            raise ValueError("Unexpected or identifier-bearing model columns")
        fields[name] = {("Column", c["name"]) for c in table["columns"]} | {("Measure", m["name"]) for m in table.get("measures", [])}
        for row in data["tables"][name]:
            if len(row) != len(expected):
                raise ValueError("Aggregate row width mismatch")
        if len(data["tables"][name]) != manifest["table_rows"][name]:
            raise ValueError("Aggregate counts differ from build manifest")
        for partition in table["partitions"]:
            if partition["source"]["type"] != "m" or not partition["source"]["expression"].startswith("#table(type table ["):
                raise ValueError("Only embedded aggregate snapshots are permitted")
    cohorts = data["tables"]["Cohorts"]
    if {row[0] for row in cohorts} != {"Brain", "Breast", "Prostate", "Skin", "Liver"}:
        raise ValueError("All five independent cohorts are required")
    for row in data["tables"]["SurgeryEvaluation"]:
        if not 0 <= row[3] <= row[2] or abs(row[4] - row[3]/row[2]) > 1e-10:
            raise ValueError("Surgery prevalence/denominator inconsistency")
        if any(not 0 <= value <= 1 for value in row[4:]):
            raise ValueError("Invalid probability or score")
    for row in data["tables"]["SurgeryCalibration"]:
        if row[-1] < 30 or not 0 <= row[3] <= 1 or not 0 <= row[4] <= 1:
            raise ValueError("Calibration group lacks support")
    for row in data["tables"]["TreatmentPatterns"]:
        if row[4] == "Suppressed" and row[3] is not None:
            raise ValueError("Suppressed counts must remain missing")
    measures = {m["name"]: m for m in tables["Cohorts"]["measures"]}
    for name in ["Surgery ROC AUC", "Surgery average precision", "Surgery Brier", "Survival C-index", "Index patients"]:
        if "HASONEVALUE(Cohorts[Cohort])" not in measures[name]["expression"]:
            raise ValueError("Metrics must not aggregate across cancer types")
    for relationship in model["model"]["relationships"]:
        for prefix in ["from", "to"]:
            if ("Column", relationship[prefix+"Column"]) not in fields[relationship[prefix+"Table"]]:
                raise ValueError("Relationship points to a missing field")
    pbir = json.loads((project / "CancerPatientAtlas.Report/definition.pbir").read_text(encoding="utf-8"))
    if pbir["datasetReference"]["byPath"]["path"] != "../CancerPatientAtlas.SemanticModel":
        raise ValueError("Report must reference its local semantic model")
    definition = project / "CancerPatientAtlas.Report/definition"
    order = json.loads((definition / "pages/pages.json").read_text(encoding="utf-8"))
    if len(order["pageOrder"]) != 7 or len(set(order["pageOrder"])) != 7:
        raise ValueError("Seven uniquely named report pages are required")
    visuals = 0
    for page_name in order["pageOrder"]:
        folder = definition / "pages" / page_name
        page = json.loads((folder / "page.json").read_text(encoding="utf-8"))
        if page["name"] != page_name:
            raise ValueError("Page path/name mismatch")
        for path in (folder / "visuals").glob("*/visual.json"):
            visual = json.loads(path.read_text(encoding="utf-8"))
            position = visual["position"]
            if position["x"] < 0 or position["y"] < 0 or position["x"]+position["width"] > page["width"] or position["y"]+position["height"] > page["height"]:
                raise ValueError("Visual exceeds page bounds")
            for role in visual["visual"].get("query", {}).get("queryState", {}).values():
                for item in role["projections"]:
                    kind = next(iter(item["field"]))
                    field = item["field"][kind]
                    entity = field["Expression"]["SourceRef"]["Entity"]
                    if entity not in fields or (kind, field["Property"]) not in fields[entity]:
                        raise ValueError("Visual references a missing model field")
            visuals += 1
    if any(p.name in {"cache.abf", "localSettings.json"} or p.suffix in {".pbix", ".csv", ".xlsx"} for p in project.rglob("*") if p.is_file()):
        raise ValueError("Cache, workbook or binary data artifact in public project")
    schema_count = validate_schemas(project) if schemas else 0
    return {"pages": 7, "tables": len(tables), "visuals": visuals, "schema_documents": schema_count, "synthetic": manifest["synthetic"]}


def validate_schemas(project):
    cache = {}

    def retrieve(uri):
        if uri not in cache:
            parsed = urlparse(uri)
            if parsed.scheme != "https" or parsed.netloc != "developer.microsoft.com" or not parsed.path.startswith("/json-schemas/fabric/"):
                raise ValueError("Only public Microsoft Power BI schema references are permitted")
            path = parsed.path.removeprefix("/json-schemas/").replace("schema.embedded.json", "schema-embedded.json")
            request = urllib.request.Request("https://raw.githubusercontent.com/microsoft/json-schemas/main/" + path,
                                             headers={"User-Agent": "CancerPatientAtlas-schema-check"})
            with urllib.request.urlopen(request, timeout=30) as response:
                contents = json.load(response)
            cache[uri] = Resource.from_contents(contents)
        return cache[uri]

    registry = Registry(retrieve=retrieve)
    count = 0
    for path in project.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".pbip", ".pbir", ".pbism"}:
            contents = json.loads(path.read_text(encoding="utf-8"))
            uri = contents.get("$schema")
            if uri:
                schema = retrieve(uri).contents
                validator = Draft7Validator({"$ref": uri}, registry=registry)
                errors = list(validator.iter_errors(contents))
                if errors:
                    raise ValueError(f"{path.relative_to(project)}: {errors[0].message} at {list(errors[0].path)}")
                count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "powerbi/PatientAtlas")
    parser.add_argument("--schemas", action="store_true", help="Validate against public Microsoft JSON schemas (network required)")
    parser.add_argument("--private", action="store_true", help="Inspect a private ignored project instead of requiring synthetic data")
    args = parser.parse_args()
    if args.private and not args.project.resolve().is_relative_to((ROOT / ".runtime").resolve()):
        raise ValueError("Private validation is restricted to ignored .runtime")
    print(json.dumps(inspect_project(args.project, public=not args.private, schemas=args.schemas)))
