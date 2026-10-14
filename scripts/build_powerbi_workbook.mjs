import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const root = process.cwd();
const sourcePath = path.join(root, "outputs", "local", "powerbi_tables.json");
const outputDir = path.join(root, "powerbi");
const qaDir = path.join(outputDir, "_qa");
const manifest = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const workbook = Workbook.create();
const fontFamily = "Arial";

function columnName(index) {
  let result = "";
  let n = index + 1;
  while (n > 0) {
    n -= 1;
    result = String.fromCharCode(65 + (n % 26)) + result;
    n = Math.floor(n / 26);
  }
  return result;
}

function tableName(label, index) {
  const cleaned = label.replace(/[^A-Za-z0-9]/g, "");
  return `PBI${index + 1}${cleaned}`.slice(0, 250);
}

const readme = workbook.worksheets.add("ReadMe");
readme.showGridLines = false;
readme.getRange("A2:H2").values = [[manifest.title]];
readme.getRange("A2:H2").format.font = { name: fontFamily, size: 16, bold: true, color: "#000000" };
readme.getRange("A3:H3").format.borders = { bottom: { style: "thin", color: "#1F4E78" } };
readme.getRange("A5:B8").values = [
  ["Purpose", "Import these aggregate tables into Power BI to build the interactive report."],
  ["Scope", manifest.scope],
  ["Interpretation", manifest.warning],
  ["Refresh", "Run the analysis scripts and rebuild this workbook before refreshing the Power BI semantic model."],
];
readme.getRange("A5:A8").format.font = { name: fontFamily, size: 10, bold: true };
readme.getRange("B5:B8").format.font = { name: fontFamily, size: 10 };
readme.getRange("A5:B8").format.verticalAlignment = "center";
readme.getRange("A5:B8").format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
readme.getRange("A5:A8").format.fill = "#D9EAF7";
readme.getRange("A:A").format.columnWidth = 18;
readme.getRange("B:B").format.columnWidth = 72;
readme.getRange("B5:B8").format.wrapText = true;
readme.getRange("A5:B8").format.autofitRows();
readme.tabColor = "#1F4E78";

for (let i = 0; i < manifest.tables.length; i += 1) {
  const table = manifest.tables[i];
  const sheetName = table.name.slice(0, 31);
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const matrix = [table.columns, ...table.rows];
  const lastColumn = columnName(table.columns.length - 1);
  const lastRow = matrix.length;
  const range = sheet.getRange(`A1:${lastColumn}${lastRow}`);
  range.values = matrix;
  range.format.font = { name: fontFamily, size: 10, color: "#222222" };
  range.format.verticalAlignment = "center";
  const header = sheet.getRange(`A1:${lastColumn}1`);
  header.format.fill = "#1F4E78";
  header.format.font = { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" };
  header.format.horizontalAlignment = "center";
  header.format.borders = { preset: "all", style: "thin", color: "#FFFFFF" };
  sheet.freezePanes.freezeRows(1);
  const excelTable = sheet.tables.add(`A1:${lastColumn}${lastRow}`, true, tableName(table.name, i));
  excelTable.style = "TableStyleMedium2";
  excelTable.showBandedRows = true;
  for (let c = 0; c < table.columns.length; c += 1) {
    const values = [table.columns[c], ...table.rows.map((row) => row[c])];
    const maxLength = Math.max(...values.slice(0, 250).map((value) => String(value ?? "").length));
    sheet.getRange(`${columnName(c)}:${columnName(c)}`).format.columnWidth = Math.max(11, Math.min(28, maxLength + 2));
    const key = table.columns[c].toLowerCase();
    if (/(records|events|negative|positive|degrees_of_freedom|n_risk)$/.test(key)) {
      sheet.getRange(`${columnName(c)}2:${columnName(c)}${lastRow}`).format.numberFormat = "#,##0";
    } else if (/(auc|accuracy|precision|recall|specificity|survival|incidence|fraction|percent|ratio|score|loss|importance|threshold|p_value|ci_low|ci_high|f1)$/.test(key)) {
      sheet.getRange(`${columnName(c)}2:${columnName(c)}${lastRow}`).format.numberFormat = "0.0000";
    }
  }
}

workbook.recalculate();
const check = await workbook.inspect({
  kind: "table",
  sheetId: "Model metrics",
  range: "A1:W8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 23,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(qaDir, { recursive: true });
for (const sheetName of ["ReadMe", "Model metrics"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(qaDir, `${sheetName.replace(/ /g, "_")}.png`),
    new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
const finalPath = path.join(outputDir, "cancer_suicide_risk_dashboard_data.xlsx");
await output.save(finalPath);
const savedWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(finalPath));
const savedCheck = await savedWorkbook.inspect({ kind: "sheet,table", maxChars: 5000, tableMaxRows: 2, tableMaxCols: 6 });
console.log(savedCheck.ndjson);
console.log(finalPath);
