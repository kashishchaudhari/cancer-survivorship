// KPI brief: one descriptive population at a time, plus a separate care study.
async function initializeObservatory() {
  const [cube, response, manifestResponse] = await Promise.all([load('raw_zip_full_eda_cube.csv'),fetch('data/care_summary.json'),fetch('data/manifest.json')]);
  if (!response.ok || !manifestResponse.ok) throw new Error('The KPI brief requires a validated local build.');
  const care = await response.json();
  const manifest = await manifestResponse.json();
  const number = new Intl.NumberFormat('en-US');
  const cohorts = [...new Set(cube.map(row=>row.source_cohort))].sort();
  options('brief-cohort',cohorts,'All supplied extracts');
  function counts(rows) {
    const total = rows.reduce((sum,row)=>sum+Number(row.patient_count),0);
    const known = rows.filter(row=>row.outcome_state!=='Outcome unavailable').reduce((sum,row)=>sum+Number(row.patient_count),0);
    const events = rows.filter(row=>row.outcome_state==='Suicide outcome recorded').reduce((sum,row)=>sum+Number(row.patient_count),0);
    return {total,known,events,missing:total-known,coverage:total?100*known/total:0};
  }
  function render() {
    const selection = document.getElementById('brief-cohort').value;
    const rows = selection==='All'?cube:cube.filter(row=>row.source_cohort===selection);
    const metric = counts(rows);
    document.getElementById('brief-total').textContent=number.format(metric.total);
    document.getElementById('brief-coverage').textContent=metric.coverage.toFixed(1)+'%';
    document.getElementById('brief-missing').textContent=number.format(metric.missing);
    document.getElementById('brief-events').textContent=number.format(metric.events);
    document.getElementById('brief-known-detail').textContent=number.format(metric.known)+' / '+number.format(metric.total)+' index patients';
    document.getElementById('brief-event-detail').textContent=metric.known?`${(100*metric.events/metric.known).toFixed(3)}% among known outcomes · variable follow-up`:'No known-outcome denominator';
    document.getElementById('brief-scope').textContent=(selection==='All'?'All supplied extracts':selection+' index cohort')+' · one earliest included diagnosis per linked patient';
    document.getElementById('brief-known-label').textContent='Recorded '+metric.coverage.toFixed(1)+'%';
    document.getElementById('brief-missing-label').textContent='Unavailable '+(metric.total?100*metric.missing/metric.total:0).toFixed(1)+'%';
    document.getElementById('brief-known-strip').style.width=metric.coverage+'%';
    document.getElementById('brief-missing-strip').style.width=(100-metric.coverage)+'%';
    document.getElementById('brief-strip').setAttribute('aria-label',`Outcome recorded for ${metric.known} of ${metric.total} index patients; ${metric.missing} unavailable.`);
    document.getElementById('brief-blindspot').textContent=metric.missing?`${number.format(metric.missing)} index patients have unavailable outcomes in this selection. They remain visible here, and are excluded from the recorded-outcome fraction.`:'Every index patient in this selection has a recorded outcome. That coverage does not establish representative sampling or clinical validity.';
    const all = cohorts.map(cohort=>({cohort,...counts(cube.filter(row=>row.source_cohort===cohort))}));
    Plotly.react('brief-constellation',[{type:'scatter',mode:'markers',x:all.map(item=>item.coverage),y:all.map(item=>item.cohort),marker:{size:all.map(item=>Math.max(15,Math.sqrt(item.total/Math.max(1,...all.map(group=>group.total)))*51)),color:all.map(item=>item.coverage<50?'#b78342':'#147d70'),opacity:all.map(item=>selection==='All'||selection===item.cohort?1:.22),line:{color:'#ffffff',width:2}},customdata:all.map(item=>[item.total,item.known,item.missing]),hovertemplate:'%{y}<br>Outcome coverage: %{x:.1f}%<br>Index patients: %{customdata[0]:,}<br>Known outcomes: %{customdata[1]:,}<br>Unavailable: %{customdata[2]:,}<extra></extra>'}],{height:300,margin:{l:70,r:33,t:15,b:47},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'Segoe UI, sans-serif',size:11,color:'#62757a'},xaxis:{title:'Outcome coverage (%)',range:[-5,106],ticksuffix:'%',gridcolor:'#e2e8df',zeroline:false},yaxis:{autorange:'reversed',gridcolor:'#edf0e9',zeroline:false},showlegend:false},{responsive:true,displayModeBar:false});
  }
  document.getElementById('brief-cohort').addEventListener('change',render);
  document.getElementById('brief-care-title').textContent=care.cohort+' / a separate care-timing study';
  document.getElementById('brief-care-population').textContent=`${number.format(care.index_patients)} index patients · ${care.diagnosis_year_start}–${care.diagnosis_year_end}. These KPIs keep their own population.`;
  document.getElementById('brief-care-timing').textContent=(100*care.timing_known_patients/care.index_patients).toFixed(1)+'%';
  document.getElementById('brief-care-followup').textContent=(100*care.followup_usable_patients/care.index_patients).toFixed(1)+'%';
  document.getElementById('brief-build').textContent=(manifest.synthetic?'Invented demonstration':'Confidential local study')+' / build '+new Date(manifest.built_at_utc).toLocaleDateString();
  document.getElementById('brief-contracts').textContent=`${manifest.checks.length} aggregate checks · ${manifest.tables.length} datasets`;
  document.getElementById('open-care-study').addEventListener('click',()=>document.querySelector('[data-view="care"]').click());
  render();
}
initializeObservatory().catch(error=>{document.getElementById('brief-scope').textContent='KPI data issue: '+error.message;});
