// Fail closed unless the Pages payload is a synthetic, static dashboard.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,readdirSync} from 'node:fs';
import {join,relative,sep} from 'node:path';

const at=process.argv.indexOf('--site');
const site=at<0?'.runtime/public-demo-site':process.argv[at+1];
function files(folder){return readdirSync(folder,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?files(join(folder,entry.name)):[relative(site,join(folder,entry.name)).split(sep).join('/')]);}
const expected=new Set(['index.html','atlas.css','atlas.js','data/catalog.json',...['brain','breast','prostate','skin','liver'].map(name=>`data/${name}.json`)]);
const withObservatory=process.argv.includes('--with-observatory');
const observatoryTables=['raw_zip_full_eda_cube.csv','raw_zip_model_comparison.csv','km_curves.csv','competing_risk_curves.csv','km_60months.csv','logrank_tests.csv','care_field_audit.csv','care_timing_cube.csv','care_survival.csv'];
if(withObservatory){for(const name of ['index.html','engineering.js','care.js','observatory.js','observatory.css','data/manifest.json','data/care_summary.json',...observatoryTables.map(n=>'data/'+n)])expected.add('observatory/'+name);}
const actual=new Set(files(site));
assert.deepEqual([...actual].sort(),[...expected].sort(),'public payload must match the static file allowlist exactly');
const catalog=JSON.parse(readFileSync(join(site,'data/catalog.json'),'utf8'));
assert.equal(catalog.synthetic,true,'public catalog must be marked synthetic');
assert.equal(catalog.studies.length,5,'all five separate studies should be present');
for(const entry of catalog.studies){
  const data=JSON.parse(readFileSync(join(site,'data',entry.file),'utf8'));
  assert.equal(data.synthetic,true,`${entry.cohort} must be marked synthetic`);
  assert.equal(data.cohort,entry.cohort,'cohort file mismatch');
  const content=JSON.stringify(data);
  assert.ok(!content.includes(`invented-${entry.cohort}-`),'individual synthetic IDs must not be exported');
  for(const field of ['patient_id','patientid','record_id','medical_record_number'])assert.ok(!content.toLowerCase().includes(field),'potential row identifier in published data');
}
const html=readFileSync(join(site,'index.html'),'utf8');
const js=readFileSync(join(site,'atlas.js'),'utf8');
assert.ok(html.includes('id="footer-classification"'),'classification disclaimer footer missing');
assert.ok(js.includes('app.synthetic=Boolean(catalog.synthetic)'),'synthetic mode is not initialized from catalog');
assert.ok(js.includes('Individual profile scoring is disabled in this public demo'),'synthetic profile scoring guard is missing');
if(withObservatory){
  const manifest=JSON.parse(readFileSync(join(site,'observatory/data/manifest.json'),'utf8'));
  assert.equal(manifest.synthetic,true,'original observatory must use invented fixtures');
  assert.deepEqual(manifest.tables.map(t=>t.name).sort(),observatoryTables.slice().sort());
  for(const entry of manifest.tables){
    const contents=readFileSync(join(site,'observatory/data',entry.name));
    assert.equal(createHash('sha256').update(contents).digest('hex'),entry.sha256,'observatory table differs from validated synthetic build');
    const header=contents.toString('utf8').split(/\r?\n/)[0];
    assert.ok(!/patient_id|patientid|record_id|medical_record_number/i.test(header),'identifier field in observatory payload');
  }
  const care=JSON.parse(readFileSync(join(site,'observatory/data/care_summary.json'),'utf8'));
  assert.ok(care.scope.includes('SYNTHETIC'),'care fixture provenance required');
}
console.log(`Public demo privacy check passed: ${actual.size} allowlisted static files, five synthetic cohorts, no record identifiers/models.`);
