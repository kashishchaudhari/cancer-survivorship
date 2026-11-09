'use strict';
const el = id => document.getElementById(id);
const count = new Intl.NumberFormat('en-US');
const fixed = n => n.toFixed(3);
let researchData;
function renderResearch() {
  const study = researchData.studies.find(s => s.cohort === el('cohort').value);
  const primary = el('design').value === 'primary';
  const metrics = primary ? study.primary : study.temporal;
  el('patients').textContent = count.format(study.index_patients);
  el('records').textContent = count.format(study.source_rows);
  el('median').textContent = study.median_days + ' days';
  el('unknown').textContent = study.unknown_timing_pct.toFixed(1) + '%';
  el('unknown-bar').style.width = study.unknown_timing_pct + '%';
  el('timing-note').textContent = study.unknown_timing_pct.toFixed(1) + '% of this cohort has unavailable timing. The median describes only calculable, non-top-coded values; it is not the experience of every patient.';
  el('iqr').textContent = study.timing_iqr.join('–') + ' days';
  el('sd').textContent = study.timing_sd.toFixed(1) + ' days';
  el('stage').textContent = study.stage_available ? 'Summary stage available' : 'Unavailable in coursework source';
  el('design-note').textContent = primary ? 'Primary: patient holdout, development-only cross-validation. The test set does not select regularization.' : 'Secondary: test diagnoses in 2016–2017. This is a different test population from the patient holdout.';
  el('auc').textContent = fixed(metrics.auc);
  el('interval').textContent = primary ? '95% fixed-model bootstrap interval: ' + study.primary.auc_ci.map(fixed).join('–') + '. This is internal evaluation.' : 'No temporal AUC interval is included in the published summary. It is not inferred from the primary interval.';
  el('test-n').textContent = count.format(metrics.test_n);
  el('brier').textContent = fixed(metrics.brier);
  el('ap-section').hidden = !primary;
  el('ap').textContent = fixed(study.primary.ap);
  el('baseline').textContent = fixed(study.primary.prevalence);
  el('ap-bar').style.width = (100 * study.primary.ap) + '%';
  el('baseline-bar').style.width = (100 * study.primary.prevalence) + '%';
  el('finding-title').textContent = study.cohort + ': interpret the denominator first.';
  el('finding').textContent = study.cohort === 'Liver' ? 'Liver supports a stage-aware analysis, unlike the four coursework sources. Its model evaluation and descriptive timing summaries use different eligible populations. Stage availability improves what can be studied; it does not establish treatment effectiveness.' : 'The descriptive cohort contains ' + count.format(study.index_patients) + ' earliest-index patients, while this evaluation includes ' + count.format(metrics.test_n) + ' test patients with eligible, known surgery codes. Stage is unavailable in this source. Those exclusions matter when communicating findings.';
  el('case-link').href = 'https://github.com/kashishchaudhari/cancer-survivorship/blob/main/docs/' + study.cohort.toUpperCase() + '_STUDY.md';
}
fetch('research-results.json').then(response => {
  if (!response.ok) throw new Error('Published results could not be loaded.');
  return response.json();
}).then(data => {
  if (data.synthetic !== false || data.studies.length !== 5) throw new Error('Unexpected research payload.');
  researchData = data;
  renderResearch();
  el('research').hidden = false;
  el('status').textContent = '';
}).catch(error => { el('status').textContent = error.message; });
el('cohort').addEventListener('change', renderResearch);
el('design').addEventListener('change', renderResearch);
