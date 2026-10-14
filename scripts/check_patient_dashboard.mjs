// Run the actual local atlas JavaScript against invented site data and a tiny DOM.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const at=process.argv.indexOf('--site');
const site=at<0?'.runtime/patient-demo-site':process.argv[at+1];
const html=readFileSync('patient_dashboard/index.html','utf8');
const script=readFileSync('patient_dashboard/atlas.js','utf8');
new vm.Script(script);
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
assert.equal(new Set(ids).size,ids.length,'DOM IDs must be unique');
for(const view of ['distribution','care','treatment-model','survival','evaluation','forecast','evidence']){
  assert.ok(ids.includes(view),`missing research view ${view}`);
  assert.ok(html.includes(`data-view="${view}"`),`missing navigation control ${view}`);
}
const catalog=JSON.parse(readFileSync(`${site}/data/catalog.json`,'utf8'));
assert.equal(catalog.studies.length,5,'four course archives and the independent Liver raw study');
assert.equal(catalog.synthetic,true,'the generated site fixture must be synthetic');
const data=Object.fromEntries(catalog.studies.map(item=>[item.cohort,JSON.parse(readFileSync(`${site}/data/${item.file}`,'utf8'))]));
for(const cohort of ['Brain','Breast','Prostate','Skin']) assert.equal(data[cohort].stage_filters.length,0,`${cohort} has no stage field`);
assert.ok(data.Liver.stage_filters.length>0,'invented Liver fixture exercises the stage controls');
for(const study of Object.values(data)){
  assert.equal(study.synthetic,true,'all displayed fixture values must be marked synthetic');
  assert.ok(study.treatment_assignment.test,'synthetic treatment assignment model should be evaluable');
  assert.ok(!JSON.stringify(study).includes(`invented-${study.cohort}-`),'no patient ID values may enter dashboard JSON');
}
// Exercise local-only interaction paths with in-memory synthetic fixtures. This
// does not alter the generated files or public demo payload.
catalog.synthetic=false;
for(const study of Object.values(data))study.synthetic=false;

class Element{
  constructor(id=''){this.id=id;this.value='All';this.textContent='';this.disabled=false;this.checked=false;this.options=[];this.children=[];this.listeners={};this.dataset={};this.classList={toggle(){},add(){},remove(){}};}
  addEventListener(name,fn){this.listeners[name]=fn;}
  append(...items){for(const item of items){this.children.push(item);if(this.tag==='select'){this.options.push(item);if(this.options.length===1)this.value=item.value;}if(item.id)elements.set(item.id,item);}}
  replaceChildren(...items){this.children=[...items];if(this.tag==='select'){this.options=[...items];this.value=items[0]?.value??'';}for(const item of items)if(item.id)elements.set(item.id,item);}
}
const elements=new Map(ids.map(id=>[id,new Element(id)]));
for(const button of elements.values()){
  if(button.id==='stage'||button.id==='age'||button.id==='sex'||button.id==='grade'||button.id==='compare'||button.id==='calibration-horizon'||button.id==='percent')button.tag='select';
}
const studyButtons=['Brain','Breast','Prostate','Skin','Liver'].map(name=>{const el=new Element();el.dataset.study=name;return el;});
const viewButtons=['distribution','care','treatment-model','survival','evaluation','forecast','evidence'].map(name=>{const el=new Element();el.dataset.view=name;return el;});
const pages=viewButtons.map(el=>{const page=new Element(el.dataset.view);page.id=el.dataset.view;return page;});
const document={
  getElementById:id=>elements.get(id),
  createElement:tag=>{const el=new Element();el.tag=tag;return el;},
  querySelectorAll:selector=>selector==='[data-study]'?studyButtons:selector==='[data-view]'?viewButtons:selector==='.page'?pages:[],
};
const rendered=new Set();
let request;
const fetch=async(url,options={})=>{
  if(url==='data/catalog.json')return{ok:true,json:async()=>catalog};
  if(url.startsWith('data/')){const name=url.slice(5);const entry=catalog.studies.find(item=>item.file===name);return{ok:true,json:async()=>data[entry.cohort]};}
  if(url==='/api/treatment-assignment'){
    request=JSON.parse(options.body);
    return{ok:true,json:async()=>({probability:.42,interpretation:'Historical source coding pattern; not a treatment recommendation.'})};
  }
  throw new Error(`Unexpected request: ${url}`);
};
const Plotly={react:(id)=>rendered.add(id)};
vm.runInNewContext(script,{document,fetch,Plotly,Intl,Number,String,Object,Math,Promise,console});
await new Promise(resolve=>setTimeout(resolve,10));
assert.ok(rendered.has('timing-hist'),'interactive timing histogram rendered');
studyButtons.find(button=>button.dataset.study==='Liver').listeners.click();
assert.equal(elements.get('stage').disabled,false,'Liver stage control is enabled');
viewButtons.find(button=>button.dataset.view==='care').listeners.click();
assert.ok(rendered.has('stage-care-matrix'),'Liver treatment-by-stage heatmap rendered');
elements.get('stage').value=data.Liver.stage_filters[0];
elements.get('stage').listeners.change();
studyButtons.find(button=>button.dataset.study==='Brain').listeners.click();
assert.equal(elements.get('stage').disabled,true,'stage control is disabled where source has no field');
viewButtons.find(button=>button.dataset.view==='treatment-model').listeners.click();
assert.ok(rendered.has('assignment-calibration'),'treatment model calibration rendered');
assert.ok(elements.has('assignment-age_mid'),'interactive treatment form includes a source age band');
elements.get('assignment-predict').listeners.click();
await new Promise(resolve=>setTimeout(resolve,10));
assert.equal(request.cohort,'Brain');
assert.ok(typeof request.features.age_mid==='number');
assert.ok(elements.get('assignment-message').textContent.includes('not a treatment recommendation'));
console.log('Cancer Patient Atlas passed 5-study fixture, stage-scope, chart, temporal-model, and API interaction checks.');
