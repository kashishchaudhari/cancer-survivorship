# Power BI Patient Atlas

An editable seven-page report for Brain, Breast, Prostate, Skin, and Liver, following the Patient Atlas palette. Pages cover cohort overview, recorded care, surgery evaluation, calibration, survival, comparison, and methods.

**All checked-in data are invented aggregates.** No patient rows, source extracts, or individual predictions are included. Results illustrate internal evaluation, not validated clinical or population risk estimates.

## Open in Power BI Desktop

1. Clone or download the whole repository.
2. Open `PatientAtlas/CancerPatientAtlas.pbip` in a current Power BI Desktop release with project support enabled.
3. Choose **Refresh**, then select a cancer and evaluation strategy.

Keep the report and semantic-model folders together. The embedded snapshot requires no database credentials or source paths. GitHub hosts editable files, not an interactive Power BI service report. Save a `.pbix` locally from Desktop if needed; these files remain ignored.

Patient holdout is the primary evaluation and temporal holdout is a sensitivity analysis. Measures require one selected cancer rather than averaging scores across cancers. Small descriptive counts remain suppressed.

## Rebuild

```shell
uv sync --locked
uv run python scripts/build_powerbi_atlas.py --synthetic
uv run python scripts/check_powerbi_project.py --schemas
```

For refreshed authorized local patient-study aggregates:

```shell
uv run python scripts/build_powerbi_atlas.py --source .runtime/patient-studies --output .runtime/powerbi-private
uv run python scripts/check_powerbi_project.py --project .runtime/powerbi-private --private
```

Private builds are restricted to ignored `.runtime` folders. Preserve original sources and keep existing confidential workbook exports local. Regeneration updates the embedded snapshot; Desktop Refresh reloads that snapshot rather than rerunning Python models.

## Validation

Checks cover Microsoft report JSON schemas, visual field bindings, layout bounds, model relationships, cohort coverage, metric guards, and synthetic classification. **Native Power BI Desktop rendering has not been verified.** Open the project in Desktop before presenting it. No service workspace or Publish to Web deployment is included.

The project uses PBIP, PBIR, and an M/TMSL semantic model. See [Microsoft documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview).
