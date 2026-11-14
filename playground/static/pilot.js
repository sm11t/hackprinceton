const $ = id => document.getElementById(id);
const money = n => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
$('aerial').addEventListener('error', () => {$('aerial').hidden = true; $('aerial-error').hidden = false;});
async function json(url, options) { const r = await fetch(url, options); const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Request failed'); return data; }
async function loadEvidence() {
  try {
    const e = await json('/api/pilot/evidence');
    $('evidence-status').textContent = e.source + (e.error ? ' · Matterport measurements unavailable' : '');
    $('building-area').textContent = e.building_area ? `${e.building_area.toLocaleString()} sq ft` : 'Building area unavailable';
    $('building-fact').textContent = 'CoStar property 23296 · entire building, not the advertised suite.';
    $('scan-area').textContent = e.warehouse_area_m2 ? `${Math.round(e.warehouse_area_m2 * 10.7639).toLocaleString()} sq ft warehouse room` : 'Room area unavailable';
    $('scan-fact').textContent = e.scan_name ? `Matterport: “${e.scan_name.trim()}”. Room area is a scan estimate, not suite area.` : 'Matterport measurements unavailable. The linked tour remains accessible above.';
    $('scan-height').textContent = e.warehouse_height_m ? `Scan-estimated room height: ${e.warehouse_height_m.toFixed(2)} m. This does not verify the advertised suite’s clear height or obstructions.` : 'Warehouse height returns 0 / unavailable, not a measured clear height. Do not use office-room heights to infer warehouse clearance.';
    if (e.model_ids.length) {const url = 'https://my.matterport.com/show/?m=' + encodeURIComponent(e.model_ids[0]); if ($('tour').src !== url) $('tour').src = url; $('tour-link').href = url;}
  } catch (error) { $('evidence-status').textContent = 'Property evidence unavailable'; $('building-fact').textContent = 'Could not load the CoStar record. Check the local sponsor kit.'; $('scan-fact').textContent = 'Measurements unavailable; confirm suite identity before relying on the tour.'; }
}
let revision = 0, timer;
function render(data) {
  const results = data.results, reserve = data.inputs.reserve;
  results.forEach((r, i) => {
    const target = $(i ? 'pickleball-result' : 'warehouse-result');
    target.replaceChildren();
    const value = document.createElement('strong'); value.textContent = `${money(r.lowest_cash)} lowest cash`;
    const detail = document.createElement('span'); detail.textContent = `Month ${r.lowest_month} · Opens month ${r.opening_month}${r.opening_month > 24 ? ' (outside chart)' : ''} · ${r.first_month_below_reserve ? `Below reserve in month ${r.first_month_below_reserve}; ${money(r.extra_funding_needed)} funding gap` : 'Stays at or above reserve'}`;
    target.append(value, detail);
  });
  const series = results.map(r => [data.starting_cash, ...r.rows.map(row => row.cash)]);
  const min = Math.min(0, reserve, ...series.flat()), max = Math.max(1, reserve, ...series.flat());
  const pad = (max-min)*.08, low = min-pad, high = max+pad;
  const x = i => 70+i/24*666, y = v => 280-(v-low)/(high-low)*245;
  const svg = $('chart'); svg.replaceChildren();
  function node(tag, attrs, text) {const n = document.createElementNS('http://www.w3.org/2000/svg', tag); Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v)); if(text!==undefined)n.textContent=text;svg.append(n);return n;}
  for(let i=0;i<5;i++){const v=min+(max-min)*i/4;node('line',{x1:70,x2:736,y1:y(v),y2:y(v),stroke:'#e4e9e2'});node('text',{x:60,y:y(v)+4,'text-anchor':'end',fill:'#6a786e','font-size':11},money(v));}
  [0,6,12,18,24].forEach(i=>node('text',{x:x(i),y:308,'text-anchor':'middle',fill:'#6a786e','font-size':12},`M${i}`));
  node('line',{x1:70,x2:736,y1:y(reserve),y2:y(reserve),stroke:'#a0783e','stroke-dasharray':'6 5','stroke-width':2});
  series.forEach((points,i)=>node('polyline',{points:points.map((v,m)=>`${x(m)},${y(v)}`).join(' '),fill:'none',stroke:i?'#26714f':'#77899c','stroke-width':3}));
  $('cash-rows').replaceChildren(); results[0].rows.forEach((row,i)=>{const tr=document.createElement('tr'); [row.month,money(row.cash),money(results[1].rows[i].cash),money(reserve)].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});$('cash-rows').append(tr);});
  const sport=results[1];
  $('finance-status').textContent = sport.first_month_below_reserve ? `Pickleball crosses the ${money(reserve)} reserve in month ${sport.first_month_below_reserve}. Cover a ${money(sport.extra_funding_needed)} gap or revise the plan.` : `Pickleball stays at or above the ${money(reserve)} reserve over 24 months. Physical fit and approvals still need confirmation.`;
  $('buyer').textContent = `${data.buyer_source}. Starting cash ${money(data.starting_cash)}; shared recurring bills ${money(data.monthly_bills)}/month (demo: $8,500 rent + $2,000 NNN). Month 0 is starting cash. Carry continues during delays.`;
}
async function update(version) {
  if (!$('assumptions').checkValidity()) { $('finance-status').textContent='Enter valid values in all fields. The chart shows the last valid scenario.'; return; }
  $('finance-status').textContent='Updating cash flow…';
  try {const inputs=Object.fromEntries([...new FormData($('assumptions'))].map(([k,v])=>[k,Number(v)])); const data=await json('/api/pilot/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(inputs)});if(version===revision)render(data);}
  catch(error){if(version===revision)$('finance-status').textContent=`Could not update: ${error.message}. Chart shows the last successful scenario.`;}
}
function schedule(){const version=++revision;clearTimeout(timer);timer=setTimeout(()=>update(version),180);}
document.querySelectorAll('input').forEach(input=>input.addEventListener('input',schedule));
$('assumptions').addEventListener('submit',e=>e.preventDefault());
$('assumptions').addEventListener('reset',()=>setTimeout(schedule,0));
loadEvidence();update(++revision);
