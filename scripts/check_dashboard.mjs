// Syntax plus interaction smoke tests without downloading frontend dependencies.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const siteArg = process.argv.indexOf('--site');
const siteRoot = siteArg >= 0 ? process.argv[siteArg + 1] : '.runtime/demo-site';
const html = readFileSync('dashboard/index.html', 'utf8');
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).filter(Boolean);
for (const script of scripts) new vm.Script(script);
new vm.Script(readFileSync('dashboard/engineering.js', 'utf8'));
new vm.Script(readFileSync('dashboard/care.js', 'utf8'));
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
assert.equal(new Set(ids).size, ids.length, 'Duplicate DOM IDs');
for (const view of ['eda', 'survival', 'models', 'care', 'engineering', 'data']) {
  assert.ok(ids.includes(view), `Missing ${view} view`);
  assert.ok(html.includes(`data-view="${view}"`), `Missing ${view} navigation`);
}
assert.ok(html.includes("[data-variable]"), 'Survival handlers must be scoped to variable buttons');
assert.ok(!html.includes("document.querySelectorAll('.tabs button').forEach(b=>b.onclick"), 'Conflicting tab handler');
console.log(`Dashboard syntax and navigation checks passed (${ids.length} unique IDs).`);

// Execute the actual initialization against real aggregate CSVs and a small DOM
// double. This catches runtime name collisions and mis-scoped event handlers.
const elements = new Map(ids.map(id => [id, {
  id, value: 'All', options: [{value:'All'}], innerHTML:'', textContent:'',
  listeners: {}, children: [], dataset:{},
  classList:{remove(){},toggle(){}},
  addEventListener(event, handler){this.listeners[event] = handler;},
  insertAdjacentHTML(_position, text){this.innerHTML += text;},
  append(child){this.children.push(child);},
}]));
const viewButtons = ['eda','survival','models','care','engineering','data'].map(view => ({
  dataset:{view}, classList:{toggle(){}}, listeners:{},
  addEventListener(event,handler){this.listeners[event]=handler;},
}));
const variableButtons = ['cancer_site','sex','age_cat','race'].map(variable => ({
  dataset:{variable}, classList:{remove(){},add(){}},
}));
elements.set('badge', {textContent:''});
const plotted = new Map();
const context = vm.createContext({
  Intl, console, setTimeout,
  document:{
    getElementById: id => elements.get(id),
    querySelector: selector => elements.get(selector.slice(1)),
    querySelectorAll: selector => selector === '[data-view]' ? viewButtons : selector === '[data-variable]' ? variableButtons : [],
    createElement: () => ({textContent:'',children:[],append(child){this.children.push(child);this.lastChild=child;}}),
  },
  Plotly:{react(id,traces){plotted.set(id,traces);},Plots:{resize(){}}},
  fetch:async url => ({ok:true,text:async()=>readFileSync(`${siteRoot}/${url.replace(/^\.\//,'')}`,'utf8'),json:async()=>JSON.parse(readFileSync(`${siteRoot}/${url.replace(/^\.\//,'')}`,'utf8'))}),
});
for (const script of scripts) vm.runInContext(script, context);
await new Promise(resolve => setTimeout(resolve, 50));
assert.ok(!elements.get('eda').innerHTML.includes('error'), elements.get('eda').innerHTML);
for (const id of ['cohort-chart','km-chart','cif-chart','auc-chart','ap-chart']) assert.ok(plotted.has(id), `Chart did not initialize: ${id}`);
for (const button of viewButtons) assert.equal(button.onclick, undefined, 'Analysis navigation must not get a survival onclick handler');
const variable = vm.runInContext('state.variable',context);
viewButtons.find(button=>button.dataset.view==='models').listeners.click();
assert.equal(vm.runInContext('state.variable',context),variable,'Changing view changed survival grouping');
const unfilteredTotal = Number(elements.get('kpi-total').textContent.replaceAll(',',''));
elements.get('cohort').value = 'Brain';
elements.get('cohort').listeners.change();
assert.ok(Number(elements.get('kpi-total').textContent.replaceAll(',','')) < unfilteredTotal,'Cohort filter did not update counts');
variableButtons[1].onclick();
assert.equal(vm.runInContext('state.variable',context),'sex');
console.log('Runtime smoke checks passed: chart initialization, cohort filtering, and independent tab/group navigation.');
vm.runInContext(readFileSync('dashboard/engineering.js','utf8'),context);
await new Promise(resolve=>setTimeout(resolve,50));
assert.ok(plotted.has('coverage-matrix'),'Coverage heatmap failed to initialize');
assert.equal(elements.get('release-status').textContent,'All aggregate contracts passed');
const tableCount = JSON.parse(readFileSync(siteRoot + '/data/manifest.json','utf8')).tables.length;
assert.equal(elements.get('lineage-body').children.length,tableCount,'Lineage table failed to initialize');
console.log('Coverage lens and release manifest initialization passed.');
elements.get('care-survival-dimension').value='stage_group';
elements.get('care-horizon').value='12';
vm.runInContext(readFileSync('dashboard/care.js','utf8'),context);
await new Promise(resolve=>setTimeout(resolve,50));
assert.ok(!elements.get('care-population').textContent.includes('issue'),elements.get('care-population').textContent);
for(const id of ['care-age-chart','care-income-chart','care-survival-chart','care-audit-chart'])assert.ok(plotted.has(id),`Care chart failed: ${id}`);
assert.ok(plotted.get('care-survival-chart')[0].y.length,'Care survival estimates did not load');
const displayedBefore=elements.get('care-display-count').textContent;
elements.get('care-stage').value='Localized';
elements.get('care-stage').listeners.change();
assert.notEqual(elements.get('care-display-count').textContent,displayedBefore,'Care stage filter did not change displayed population');
assert.equal(elements.get('cohort').value,'Brain','Care filter changed exploratory filters');
viewButtons.find(button=>button.dataset.view==='care').listeners.click();
assert.equal(elements.get('cohort-filters').hidden,true,'Exploratory filters must be hidden in care view');
console.log('Care-equity initialization, filters, survival estimates and population boundaries passed.');
