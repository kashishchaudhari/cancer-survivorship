// A separate study population with separate filters and an all-cause endpoint.
async function initializeCareEquity() {
  const [audit, cube, survival, response] = await Promise.all([
    load('care_field_audit.csv'), load('care_timing_cube.csv'), load('care_survival.csv'), fetch('data/care_summary.json'),
  ]);
  if (!response.ok) throw new Error('Could not load care cohort metadata.');
  const summary = await response.json();
  const format = new Intl.NumberFormat('en-US');
  document.getElementById('care-population').textContent = `${summary.cohort} · ${format.format(summary.index_patients)} earliest-index patients · diagnosis ${summary.diagnosis_year_start}–${summary.diagnosis_year_end} · separate from other dashboard populations`;
  document.getElementById('care-cohort-size').textContent = format.format(summary.index_patients);
  document.getElementById('care-timing-coverage').textContent = `${(100*summary.timing_known_patients/summary.index_patients).toFixed(1)}%`;
  document.getElementById('care-followup').textContent = `${(100*summary.followup_usable_patients/summary.index_patients).toFixed(1)}%`;
  document.getElementById('care-selection-note').textContent = `${summary.selection_rule} Selected: ${summary.cohort}. Missing stage columns in other extracts are shown as 0% usable; this does not mean those cancers were unstaged.`;
  for (const [id, field] of [['care-age','age_band'],['care-income','income_band'],['care-stage','stage_group']]) options(id,cube.map(row=>row[field]),'All groups');
  const bands = ['Same day','1–30 days','31–60 days','61–90 days','91–730 days','731+ days','Unknown / unavailable'];
  const colors = ['#126d69','#269b94','#73bab0','#c29b55','#9c743e','#6b4b32','#a6b4bf'];
  const chartLayout = {margin:{l:60,r:18,t:12,b:100},height:310,font:{family:'Segoe UI, sans-serif',color:'#607283',size:10},paper_bgcolor:'transparent',plot_bgcolor:'transparent',legend:{orientation:'h',y:-.35},xaxis:{automargin:true},yaxis:{title:'Patients in reported cells',gridcolor:'#edf1f3'}};
  function renderTiming() {
    const selected = cube.filter(row=>[['care-age','age_band'],['care-income','income_band'],['care-stage','stage_group']].every(([id,field])=>document.getElementById(id).value==='All'||document.getElementById(id).value===row[field]));
    const withheld = selected.filter(row=>row.status==='Suppressed').length;
    const rows = selected.filter(row=>row.status==='Reported');
    document.getElementById('care-display-count').textContent = format.format(rows.reduce((sum,row)=>sum+Number(row.patient_count),0));
    document.getElementById('care-suppression').textContent = `${withheld} filtered cell(s) withheld (<11 patients). Counts exclude these cells.`;
    for (const [id,dimension] of [['care-age-chart','age_band'],['care-income-chart','income_band']]) {
      const categories = [...new Set(rows.map(row=>row[dimension]))].sort();
      const traces = bands.map((band,index)=>({type:'bar',name:band,x:categories,y:categories.map(category=>rows.filter(row=>row[dimension]===category&&row.timing_band===band).reduce((sum,row)=>sum+Number(row.patient_count),0)),marker:{color:colors[index]},hovertemplate:`${band}<br>%{x}<br>%{y:,} patients in reported cells<extra></extra>`}));
      Plotly.react(id,traces,{...chartLayout,barmode:'stack',annotations:rows.length?[]:[{text:'No reportable cells match these filters',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false}]},{responsive:true,displayModeBar:false});
    }
  }
  function renderSurvival() {
    const dimension = document.getElementById('care-survival-dimension').value;
    const horizon = document.getElementById('care-horizon').value;
    const rows = survival.filter(row=>row.dimension===dimension&&row.months===horizon);
    Plotly.react('care-survival-chart',[{type:'bar',x:rows.map(row=>row.category),y:rows.map(row=>100*Number(row.survival)),marker:{color:'#168c88'},error_y:{type:'data',symmetric:false,array:rows.map(row=>100*(Number(row.ci_high)-Number(row.survival))),arrayminus:rows.map(row=>100*(Number(row.survival)-Number(row.ci_low)))},customdata:rows.map(row=>[Number(row.n_risk),100*Number(row.ci_low),100*Number(row.ci_high)]),hovertemplate:'%{x}<br>All-cause survival: %{y:.1f}%<br>95% CI: %{customdata[1]:.1f}–%{customdata[2]:.1f}%<br>At risk: %{customdata[0]:,}<extra></extra>'}],{...chartLayout,showlegend:false,margin:{l:60,r:18,t:12,b:70},yaxis:{title:`${horizon}-month all-cause survival (%)`,range:[0,100],gridcolor:'#edf1f3'},annotations:rows.length?[]:[{text:'Insufficient at-risk counts for this comparison',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false}]},{responsive:true,displayModeBar:false});
  }
  for (const id of ['care-age','care-income','care-stage']) document.getElementById(id).addEventListener('change',renderTiming);
  for (const id of ['care-survival-dimension','care-horizon']) document.getElementById(id).addEventListener('change',renderSurvival);
  document.getElementById('care-reset').addEventListener('click',()=>{for(const id of ['care-age','care-income','care-stage'])document.getElementById(id).value='All';renderTiming();});
  const cohorts = [...new Set(audit.map(row=>row.cohort))];
  const fields = ['age','income','timing','stage','survival'];
  Plotly.react('care-audit-chart',[{type:'heatmap',x:['Age','Area income','Timing','Summary stage','Usable follow-up'],y:cohorts,z:cohorts.map(cohort=>fields.map(field=>100*Number(audit.find(row=>row.cohort===cohort&&row.field===field).usable_fraction))),customdata:cohorts.map(cohort=>fields.map(field=>{const row=audit.find(row=>row.cohort===cohort&&row.field===field);return [Number(row.usable_patients),Number(row.eligible_patients),row.present==='1'?'Source field present':'Source field absent'];})),zmin:0,zmax:100,colorscale:[[0,'#edf2f4'],[.5,'#7ac3bc'],[1,'#126d69']],colorbar:{title:'Usable %',thickness:12},hovertemplate:'%{y} · %{x}<br>%{z:.1f}% usable<br>%{customdata[0]:,} / %{customdata[1]:,} index patients<br>%{customdata[2]}<extra></extra>'}],{...chartLayout,margin:{l:80,r:40,t:10,b:60},yaxis:{autorange:'reversed'}},{responsive:true,displayModeBar:false});
  renderTiming();
  renderSurvival();
}
initializeCareEquity().catch(error=>{document.getElementById('care-population').textContent=`Care data issue: ${error.message}`;});
