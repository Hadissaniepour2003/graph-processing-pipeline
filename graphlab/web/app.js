'use strict';
const $ = id => document.getElementById(id);
const colors = ['#24735e','#d98244','#688ec0','#a074b4','#be5263','#86a35b','#bd9b37','#687879'];
let graph = null, analysis = null, bench = null, activeTab = 'overview', route = [], busy = false;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value, digits = 2) => value == null ? '—' : Number(value).toLocaleString(undefined, {maximumFractionDigits:digits,minimumFractionDigits:digits});
const percent = value => value == null ? '—' : number(value * 100,1) + '%';
const bytes = value => value < 1024 ? value + ' B' : value < 1048576 ? number(value/1024,1)+' KB' : number(value/1048576,1)+' MB';
function parameters() { return {partitions:Number($('partitions').value), balance_lambda:Number($('lambda').value), seed:Number($('seed').value), capacity:$('capacity').checked}; }
function applyParameters(params) { $('partitions').value=params.partitions; $('lambda').value=params.balance_lambda; $('seed').value=params.seed; $('capacity').checked=params.capacity; $('dirty').hidden=true; }
function notify(message, progress = false) { $('message').textContent=message; $('message').hidden=!message; $('message').classList.toggle('progress',progress); }
async function api(path, body, file) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(),60000);
  try {
    const response = await fetch(path,{method:body || file ? 'POST':'GET',headers:body ? {'Content-Type':'application/json'} : {},body:file || (body ? JSON.stringify(body):undefined),signal:controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The server could not process that request.');
    return data;
  } catch(error) {
    if (error.name === 'AbortError') throw new Error('This local request exceeded 60 seconds. Try a smaller graph or fewer benchmark repeats.');
    if (error instanceof TypeError) throw new Error('Cannot reach the local server. Keep the Graph Lab terminal open and refresh this page.');
    throw error;
  } finally { clearTimeout(timer); }
}
async function action(message, callback) {
  if (busy) return; busy=true;
  const controls=[...document.querySelectorAll('button,input,select,textarea')].map(el=>[el,el.disabled]);
  controls.forEach(([el])=>el.disabled=true); notify(message,true);
  try { await callback(); notify(''); }
  catch(error) { notify(error.message); }
  finally { busy=false; controls.forEach(([el,disabled])=>el.disabled=disabled); $('size').disabled=$('family').value==='sample'; renderHeader(); }
}
function selectedRun() { return activeTab==='history' ? null : activeTab==='benchmarks' ? bench : analysis; }
function renderHeader() {
  const current=selectedRun(); $('export-json').disabled=busy || !current; $('export-csv').disabled=busy || !current;
  if(activeTab==='history') { $('result-title').textContent='Saved experiments'; $('result-meta').textContent='Reopen computed results from this computer.'; }
  else if(activeTab==='benchmarks') { $('result-title').textContent=bench ? 'Benchmark · '+bench.request.family : 'Benchmark your algorithms'; $('result-meta').textContent=bench ? `Seed ${bench.request.parameters.seed} · ${bench.request.repeats} repeats · ${new Date(bench.created).toLocaleString()}` : 'Run a measured experiment below.'; }
  else if(analysis) { $('result-title').textContent=`${analysis.summary.vertices} vertices · ${analysis.summary.edges} edges`; $('result-meta').textContent=`Seed ${analysis.parameters.seed} · ${analysis.parameters.partitions} partitions · λ ${analysis.parameters.balance_lambda} · ${analysis.parameters.capacity ? 'capacity constrained':'unconstrained'} · ${new Date(analysis.created).toLocaleTimeString()}`; }
}
async function showTab(tab) {
  activeTab=tab;
  document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==tab);
  document.querySelectorAll('[data-tab]').forEach(el=>el.classList.toggle('active',el.dataset.tab===tab));
  renderHeader();
  if(tab==='history') await action('Loading saved experiments…',loadHistory);
}
function table(id, headings, rows) { $(id).innerHTML='<thead><tr>'+headings.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(cell=>'<td>'+cell+'</td>').join('')+'</tr>').join('')+'</tbody>'; }
function loadBar(loads) { const total=loads.reduce((a,b)=>a+b,0); return '<div class="load-bar">'+loads.map((v,p)=>`<span style="width:${total ? v/total*100:0}%;background:${colors[p]}"></span>`).join('')+'</div>'; }
function renderAnalysis(result) {
  analysis=result; graph=result.graph; route=[]; applyParameters(result.parameters);
  $('current-input').textContent=`Current graph: ${graph.nodes.length} vertices, ${graph.edges.length} edges.`;
  $('stats').innerHTML=[['Vertices',result.summary.vertices],['Edges',result.summary.edges],['Components',result.summary.components],['Density',percent(result.summary.density)]].map(([name,value])=>`<div class="stat"><span>${name}</span><strong>${esc(value)}</strong></div>`).join('');
  table('comparison',['Algorithm','Partition loads','Max / ideal','Edge cuts','Replication','Time (ms)'],result.partitions.map(p=>[esc(p.algorithm),esc(p.loads.join(' / '))+loadBar(p.loads),number(p.max_load_ratio)+'×',percent(p.cut_fraction),number(p.replication_factor),number(p.runtime_ms,3)]));
  const hdrf=result.partitions.find(p=>p.algorithm==='HDRF');
  $('insight').classList.toggle('warning',hdrf.max_load_ratio>1.25);
  $('insight').textContent=hdrf.max_load_ratio>1.25 ? `Watch the trade-off: HDRF uses ${hdrf.used_partitions} of ${result.parameters.partitions} partitions, with ${number(hdrf.replication_factor)} copies per active vertex but ${number(hdrf.max_load_ratio)}× max/ideal edge load. Try λ = 8 or enable the load cap, then run again.` : `HDRF’s max/ideal edge load is ${number(hdrf.max_load_ratio)}× and replication is ${number(hdrf.replication_factor)} copies per active vertex. Compare both metrics against DBH before choosing a policy.`;
  const maxPayload=Math.max(...result.storage.rows.map(r=>r.payload_bytes),1);
  $('storage-bars').innerHTML=result.storage.rows.map(r=>`<div class="storage-row"><span>${esc(r.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${r.payload_bytes/maxPayload*100}%"></div></div><span>${bytes(r.payload_bytes)}</span></div>`).join('');
  table('storage-table',['Representation','Numeric payload','Python allocation estimate'],result.storage.rows.map(r=>[esc(r.name),bytes(r.payload_bytes),bytes(r.allocated_bytes_estimate)]));
  $('storage-method').textContent=result.storage.method; $('csr').textContent=JSON.stringify(result.storage.csr_preview,null,2);
  for(const id of ['source','target']) { $(id).replaceChildren(...graph.nodes.map(node=>{const option=document.createElement('option');option.value=node;option.textContent=node;return option;})); }
  $('target').value=graph.nodes.at(-1); $('path-result').textContent='Choose two vertices and calculate a route.';
  renderGraph(); renderTrace(true); renderHeader();
}
function renderGraph() {
  if(!analysis) return;
  const selected=analysis.partitions.find(p=>p.algorithm===$('map-algorithm').value);
  const n=graph.nodes.length, edges=graph.edges;
  $('legend').innerHTML=selected.loads.map((_,p)=>`<span><i class="swatch" style="background:${colors[p]}"></i>Partition ${p}</span>`).join('')+(selected.kind==='edge' ? '<span><i class="swatch" style="background:#e6b54a"></i>Replicated vertex</span>':'');
  if(n>120 || edges.length>500) { $('graph').innerHTML='<text x="400" y="175" text-anchor="middle" fill="#60716d" font-size="15">Large graph: use the calculated metrics and exports below.</text><text x="400" y="204" text-anchor="middle" fill="#60716d" font-size="12">Interactive drawing is limited to 120 vertices and 500 edges.</text>'; $('graph-note').textContent='All vertices and edges are still included in computation.';return; }
  const positions=graph.nodes.map((_,i)=>({x:400+145*Math.cos(i*2*Math.PI/n),y:190+145*Math.sin(i*2*Math.PI/n)}));
  const lookup=new Map(graph.nodes.map((node,i)=>[node,i]));
  // Deterministic, bounded force layout. This changes drawing only, never results.
  for(let iteration=0;iteration<100;iteration++) {
    const forces=positions.map(()=>({x:0,y:0}));
    for(let i=0;i<n;i++) for(let j=i+1;j<n;j++) { const dx=positions[i].x-positions[j].x,dy=positions[i].y-positions[j].y,d2=Math.max(dx*dx+dy*dy,25),f=1400/d2; forces[i].x+=dx*f;forces[i].y+=dy*f;forces[j].x-=dx*f;forces[j].y-=dy*f; }
    for(const edge of edges) { const u=lookup.get(edge.source),v=lookup.get(edge.target),dx=positions[v].x-positions[u].x,dy=positions[v].y-positions[u].y,d=Math.max(Math.hypot(dx,dy),1),f=(d-90)*.018; forces[u].x+=dx/d*f;forces[u].y+=dy/d*f;forces[v].x-=dx/d*f;forces[v].y-=dy/d*f; }
    positions.forEach((p,i)=>{p.x=Math.min(740,Math.max(60,p.x+Math.max(-7,Math.min(7,forces[i].x))+(400-p.x)*.003));p.y=Math.min(330,Math.max(50,p.y+Math.max(-7,Math.min(7,forces[i].y))+(190-p.y)*.003));});
  }
  const routeEdges=new Set();for(let i=1;i<route.length;i++) routeEdges.add([lookup.get(route[i-1]),lookup.get(route[i])].sort((a,b)=>a-b).join(','));
  let svg='';
  edges.forEach((edge,i)=>{const u=lookup.get(edge.source),v=lookup.get(edge.target),a=positions[u],b=positions[v];const onRoute=routeEdges.has([u,v].sort((a,b)=>a-b).join(','));const color=onRoute ? '#db5f2a' : selected.kind==='edge' ? colors[selected.assignments[i]] : selected.assignments[u]===selected.assignments[v] ? colors[selected.assignments[u]] : '#a9b7ac';svg+=`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${color}" stroke-width="${onRoute?5:2}" opacity=".8"><title>${esc(edge.source)} — ${esc(edge.target)} · weight ${esc(edge.weight)}</title></line>`;if(n<=20) svg+=`<text x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2-5}" text-anchor="middle" fill="#5c6c64" font-size="11">${edge.weight}</text>`;});
  positions.forEach((p,i)=>{let color=selected.kind==='vertex' ? colors[selected.assignments[i]] : selected.replicas[i].length ? colors[selected.replicas[i][0]] : '#a9b7ac';const replicated=selected.kind==='edge' && selected.replicas[i].length>1;svg+=`<circle cx="${p.x}" cy="${p.y}" r="${n>60?8:15}" fill="${color}" stroke="${replicated?'#e6b54a':'white'}" stroke-width="3"><title>${esc(graph.nodes[i])}${replicated?' · replicated':''}</title></circle>`;if(n<=60) svg+=`<text x="${p.x}" y="${p.y+4}" text-anchor="middle" fill="white" font-size="10" font-weight="650">${esc(graph.nodes[i].slice(0,5))}</text>`;});
  $('graph').innerHTML=svg; $('graph-note').textContent=route.length ? 'The calculated shortest route is highlighted in orange.' : selected.kind==='vertex' ? 'Gray edges cross vertex partitions. Hover over an edge to inspect its weight.' : 'Edges are colored by partition. Gold rings mark vertices copied into multiple partitions.';
}
function renderTrace(reset=false) {
  if(!analysis)return;
  const part=analysis.partitions.find(p=>p.algorithm===$('trace-algorithm').value);
  const count=part.trace.length;$('trace-step').max=Math.max(0,count-1);if(reset)$('trace-step').value=0;
  const step=Math.min(Number($('trace-step').value),count-1),entry=part.trace[step];$('step-label').textContent=count ? `${step+1} / ${count}`:'0';
  if(!entry){$('trace-context').textContent='There are no edges to inspect.';$('trace-table').innerHTML='';$('trace-note').textContent='';return;}
  $('trace-context').textContent=(part.kind==='vertex' ? `Vertex ${entry.vertex}` : `Edge ${entry.source} — ${entry.target}`)+` → partition ${entry.chosen}`;
  if(part.algorithm==='DBH') { table('trace-table',['Hash anchor','Assigned partition'],[[esc(entry.hash_vertex),String(entry.chosen)]]);$('trace-note').textContent='DBH hashes the lower-degree endpoint with deterministic BLAKE2b. Equal degrees choose the target endpoint. No load cap is applied.'; }
  else { const term=part.algorithm==='FENNEL'?'Penalty':'Balance';table('trace-table',['Partition','Locality',term,'Total score','Eligible'],entry.scores.map(s=>[String(s.partition),number(s.locality,3),number(s.penalty ?? s.balance,3),number(s.score,3),s.eligible?'Yes':'No: at capacity']));const row=$('trace-table').tBodies[0].rows[entry.chosen];if(row)row.classList.add('trace-chosen');$('trace-note').textContent=part.algorithm==='FENNEL' ? `FENNEL: assigned neighbors − α[(size+1)^1.5 − size^1.5], α = ${number(part.details.alpha,4)}. Scores are before placement. Ties prefer lower load, then partition ID. Showing the first ${count} vertices.` : `HDRF: endpoint locality + λ(maxLoad − load)/(1 + maxLoad − minLoad), with λ = ${analysis.parameters.balance_lambda}. Scores are before placement. Ties prefer lower load, then partition ID. Showing the first ${count} edges.`; }
}
function renderPath(result) {
  route=result.path;
  let html=result.reachable ? `<div class="route">${result.path.map(esc).join(' → ')}<div class="hint">Total weight: ${number(result.distance)} · ${esc(result.algorithm)}</div></div><button id="show-route" class="secondary">Show route on partition map →</button>` : '<div class="route">No route connects these vertices.</div>';
  const s=result.semiring;
  html+=s.available ? `<div class="semiring-grid"><div><strong>${esc(s.exact_hop_walks)}</strong><span>Walks of exactly ${s.hops} hops</span></div><div><strong>${s.exact_hop_reachable?'Yes':'No'}</strong><span>Reachable in exactly ${s.hops} hops</span></div><div><strong>${s.min_weight_up_to_hops==null?'No route':number(s.min_weight_up_to_hops)}</strong><span>Min weight using at most ${s.hops} hops</span></div></div><p class="hint">${esc(s.explanation)}</p>` : `<p class="hint">${esc(s.reason)}</p>`;
  $('path-result').innerHTML=html; if($('show-route')) $('show-route').onclick=()=>showTab('overview');renderGraph();
}
function renderBenchmark(result) {
  bench=result;const methods=[...new Set(result.rows.map(row=>row.algorithm))];const sizes=result.request.sizes;const maxX=Math.max(...sizes),minX=Math.min(...sizes),maxY=Math.max(...result.rows.map(r=>r.median_ms),.001)*1.15;
  const x=n=>60+(n-minX)/(maxX-minX || 1)*640,y=value=>210-value/maxY*170;
  let svg='<svg class="bench-chart" viewBox="0 0 760 260" role="img" aria-label="Measured median runtime by graph vertex count"><text x="16" y="18" fill="#60716d" font-size="10">ms</text>';
  for(let t=0;t<=4;t++){const value=maxY*t/4;svg+=`<line x1="60" y1="${y(value)}" x2="700" y2="${y(value)}" stroke="#dce5da"/><text x="50" y="${y(value)+4}" text-anchor="end" font-size="10" fill="#60716d">${number(value,2)}</text>`;}
  for(const size of sizes) svg+=`<text x="${x(size)}" y="233" text-anchor="middle" font-size="10" fill="#60716d">${size}</text>`;
  methods.forEach((method,index)=>{const rows=result.rows.filter(r=>r.algorithm===method);svg+=`<polyline points="${rows.map(r=>x(r.vertices)+','+y(r.median_ms)).join(' ')}" fill="none" stroke="${colors[index]}" stroke-width="2"/>`;for(const row of rows)svg+=`<circle cx="${x(row.vertices)}" cy="${y(row.median_ms)}" r="4" fill="${colors[index]}"><title>${esc(method)}: ${row.vertices} vertices, ${number(row.median_ms,3)} ms</title></circle>`;});svg+='<text x="380" y="255" text-anchor="middle" font-size="10" fill="#60716d">Vertices</text></svg>';
  $('bench-result').innerHTML=svg+`<div class="legend">${methods.map((m,i)=>`<span><i class="swatch" style="background:${colors[i]}"></i>${esc(m)}</span>`).join('')}</div><div class="table-wrap"><table id="bench-table"></table></div><p class="hint">${esc(result.method)}</p><p class="hint">${esc(result.environment.platform)} · Python ${esc(result.environment.python)} · NumPy ${esc(result.environment.numpy)} · Seed ${result.request.parameters.seed} · λ ${result.request.parameters.balance_lambda} · ${result.request.parameters.capacity?'capacity constrained':'unconstrained'}</p>`;
  table('bench-table',['Vertices / edges','Algorithm','Median ms','Min–max ms','Max/ideal','Cuts','Replication','CSR payload'],result.rows.map(r=>[`${r.vertices} / ${r.edges}`,esc(r.algorithm),number(r.median_ms,3),`${number(r.min_ms,3)}–${number(r.max_ms,3)}`,number(r.max_load_ratio)+'×',percent(r.cut_fraction),number(r.replication_factor),bytes(r.csr_payload_bytes)]));renderHeader();
}
async function loadHistory() {
  const runs=await api('/api/runs');$('history-list').replaceChildren();
  if(!runs.length){$('history-list').textContent='No saved experiments yet.';return;}
  for(const run of runs){const div=document.createElement('div');div.className='history-row';div.innerHTML=`<div><strong>${esc(run.label)}</strong><p>${esc(run.type)} · ${esc(new Date(run.created).toLocaleString())}</p></div>`;const button=document.createElement('button');button.className='secondary';button.textContent='Reopen';button.onclick=()=>action('Opening saved experiment…',async()=>{const data=await api('/api/runs/'+run.id);if(data.type==='analysis'){renderAnalysis(data);await showTab('overview');}else{renderBenchmark(data);applyParameters(data.request.parameters);$('bench-family').value=data.request.family;$('bench-sizes').value=data.request.sizes.join(',');$('repeats').value=data.request.repeats;await showTab('benchmarks');}});div.append(button);$('history-list').append(div);}
}
async function importFile(file) { const form=new FormData();form.append('file',file);const imported=await api('/api/import',null,form);const result=await api('/api/analyze',{graph:imported,parameters:parameters()});renderAnalysis(result);await showTab('overview'); }
$('load-example').onclick=()=>action('Generating and analyzing your graph…',async()=>{const imported=await api(`/api/example?family=${encodeURIComponent($('family').value)}&size=${Number($('size').value)}&seed=${Number($('seed').value)}`);renderAnalysis(await api('/api/analyze',{graph:imported,parameters:parameters()}));await showTab('overview');});
$('family').onchange=()=>{$('size').disabled=$('family').value==='sample';};
$('csv-file').onchange=()=>{const file=$('csv-file').files[0];if(file)action('Validating CSV and computing results…',()=>importFile(file));$('csv-file').value='';};
$('paste-csv').onclick=()=>action('Validating pasted CSV…',()=>importFile(new File([$('csv-text').value],'pasted.csv',{type:'text/csv'})));
$('analyze').onclick=()=>action('Computing storage and four partitioning algorithms…',async()=>{if(!graph)throw new Error('Load a graph first.');renderAnalysis(await api('/api/analyze',{graph,parameters:parameters()}));});
for(const id of ['partitions','lambda','capacity','seed'])$(id).addEventListener('input',()=>{$('dirty').hidden=false;});
$('map-algorithm').onchange=renderGraph;
$('trace-algorithm').onchange=()=>renderTrace(true);$('trace-step').oninput=()=>renderTrace();
$('find-path').onclick=()=>action('Calculating shortest path and semiring results…',async()=>{if(!graph)throw new Error('Load a graph first.');renderPath(await api('/api/path',{graph,source:$('source').value,target:$('target').value,hops:Number($('hops').value)}));});
$('benchmark').onclick=()=>action('Benchmarking repeated runs on this computer…',async()=>{const sizes=$('bench-sizes').value.split(',').map(value=>Number(value.trim()));renderBenchmark(await api('/api/benchmark',{family:$('bench-family').value,sizes,repeats:Number($('repeats').value),parameters:parameters()}));});
$('refresh-history').onclick=()=>action('Loading saved experiments…',loadHistory);
for(const format of ['json','csv'])$('export-'+format).onclick=()=>{const result=selectedRun();if(result){const a=document.createElement('a');a.href=`/api/runs/${result.id}/export?format=${format}`;a.download='graphlab-'+result.id+'.'+format;document.body.append(a);a.click();a.remove();}};
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>showTab(button.dataset.tab));
action('Starting your local experiment…',async()=>{graph=await api('/api/example');renderAnalysis(await api('/api/analyze',{graph,parameters:parameters()}));});
