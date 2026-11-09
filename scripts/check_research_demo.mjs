// Exercise every study/design combination against the generated public payload.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const site = process.argv[2];
if (!site) throw Error('Usage: node scripts/check_research_demo.mjs SITE');
const payload = JSON.parse(readFileSync(site + '/research-results.json', 'utf8'));
assert.equal(payload.synthetic, false);
assert.deepEqual(payload.studies.map(s=>s.cohort), ['Brain','Breast','Prostate','Skin','Liver']);
const html = readFileSync(site + '/index.html', 'utf8');
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(x=>x[1]);
assert.equal(new Set(ids).size, ids.length);
const elements = Object.fromEntries(ids.map(id=>[id,{textContent:'',value:'',style:{},hidden:false,addEventListener(){}}]));
elements.cohort.value = 'Liver'; elements.design.value = 'primary';
const context = vm.createContext({document:{getElementById:id=>{
  assert.ok(elements[id], 'Unknown DOM ID: ' + id); return elements[id];
}}, Intl, fetch:async()=>({ok:true,json:async()=>payload})});
vm.runInContext(readFileSync(site + '/research.js','utf8'),context);
await new Promise(resolve=>setImmediate(resolve));
assert.equal(elements.research.hidden,false);
assert.equal(elements.status.textContent,'');
for(const study of payload.studies){
  assert.deepEqual(Object.keys(study).sort(), ['cohort','source_rows','index_patients','median_days','timing_iqr','timing_sd','unknown_timing_pct','stage_available','primary','temporal'].sort());
  assert.ok(study.index_patients <= study.source_rows);
  assert.ok(study.unknown_timing_pct >= 0 && study.unknown_timing_pct <= 100);
  for(const design of ['primary','temporal']){
    elements.cohort.value = study.cohort; elements.design.value = design;
    vm.runInContext('renderResearch()',context);
    assert.equal(elements.auc.textContent,study[design].auc.toFixed(3));
    assert.equal(elements['ap-section'].hidden,design!=='primary');
    assert.equal(elements['test-n'].textContent,new Intl.NumberFormat('en-US').format(study[design].test_n));
    assert.equal(elements['unknown-bar'].style.width,study.unknown_timing_pct+'%');
    assert.ok(elements['case-link'].href.endsWith(study.cohort.toUpperCase()+'_STUDY.md'));
  }
}
assert.ok(!JSON.stringify(payload).match(/Patient ID|file:\/\/|C:\\\\Users|private_key|password|prediction_rows/i));
console.log('Passed: 10 interactive states, denominators, AP baseline visibility, schema and private-field checks.');
