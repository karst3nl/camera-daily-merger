'use strict';
const el = id => document.getElementById(id);
let csrf = '', jobs = [];
async function api(path, options) {
  const response = await fetch(`./api/${path}`, options);
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return response.json();
}
async function refresh() {
  const status = await api('status'); csrf = status.csrf;
  el('verification').textContent = status.verification;
  const selected = el('camera').value;
  el('camera').replaceChildren(...status.cameras.map(name => {const o=document.createElement('option');o.value=name;o.textContent=name;return o;}));
  if (status.cameras.includes(selected)) el('camera').value=selected;
  el('reprocess').disabled = !status.configured;
  el('diagnostics').textContent = status.diagnostics.map(d=>`${d.camera} · ${d.day}: ${d.reason}`).join(' | ');
  if (!status.configured) el('message').textContent='Source configuration is required before processing.';
  jobs = await api('jobs');
  el('jobs').replaceChildren(...jobs.map(job=>{
    const row=document.createElement('div'); row.className='job';
    const info=document.createElement('div'), name=document.createElement('strong'), detail=document.createElement('small'), state=document.createElement('span');
    name.textContent=`${job.camera} · ${job.day}`;
    detail.textContent=job.error || `${job.attempts} processing attempt${job.attempts===1?'':'s'}`;
    state.className=`state ${job.status==='failed'?'failed':''}`; state.textContent=job.status;
    info.append(name,detail); row.append(info,state);return row;
  }));
  if (!jobs.length) {const p=document.createElement('p');p.textContent='No processing history yet.';el('jobs').append(p);}
}
function show() {
  const camera=el('camera').value, day=el('day').value;
  const job=jobs.find(j=>j.camera===camera && j.day===day && j.has_output);
  el('video').pause();el('video').removeAttribute('src');el('video').load();
  el('video').hidden=!job;el('download').hidden=!job;el('empty').hidden=Boolean(job);el('playback').hidden=true;
  if (job) {const url=`./video/${encodeURIComponent(camera)}/${encodeURIComponent(day)}`;el('video').src=url;el('download').href=`${url}?download=1`;}
  else el('empty').textContent='No completed export for this camera and date.';
}
el('show').addEventListener('click',show);
el('video').addEventListener('error',()=>{el('playback').hidden=false;});
el('refresh').addEventListener('click',()=>refresh().catch(e=>el('message').textContent=e.message));
el('reprocess').addEventListener('click',async()=>{
  el('reprocess').disabled=true;
  try {const result=await api('reprocess',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({camera:el('camera').value,day:el('day').value})});
    el('message').textContent=result.diagnostics.length?'Discovery issues blocked this day. See diagnostics.':result.queued?'Day queued for sequential processing.':'No new job queued; it may already be pending or have no eligible clips.';
    await refresh();
  } catch(e) {el('message').textContent=e.message;} finally {el('reprocess').disabled=false;}
});
refresh().catch(e=>el('message').textContent=e.message);
