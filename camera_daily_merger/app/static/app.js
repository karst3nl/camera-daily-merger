'use strict';
const el = id => document.getElementById(id);
let csrf = '', jobs = [];
async function api(path, options) {
  const response = await fetch(`./api/${path}`, options);
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return response.json();
}
function diagnosticText(d) {
  const hints = {
    filename_pattern_mismatch: 'Check timestamp_pattern and extra backslashes.',
    timestamp_format_mismatch: 'Check timestamp_format; compact digits need %Y%m%d%H%M%S.',
    ambiguous_or_nonexistent_local_time: 'The local time is ambiguous or nonexistent at a DST transition.'
  };
  const examples = d.examples && d.examples.length ? ` · File examples: ${d.examples.join(', ')}` : '';
  return `${d.camera} · ${d.day}: ${d.reason}${d.detail ? ` (${d.detail})` : ''}${Number.isInteger(d.count) ? ` · ${d.count} affected entries` : ''}${examples}${hints[d.detail] ? ` · ${hints[d.detail]}` : ''}`;
}
async function refresh() {
  const status = await api('status'); csrf = status.csrf;
  el('verification').textContent = `${status.version || 'Alpha'} · ${status.verification}`;
  const selected = el('camera').value;
  el('camera').replaceChildren(...status.cameras.map(name => {const o=document.createElement('option');o.value=name;o.textContent=name;return o;}));
  if (status.cameras.includes(selected)) el('camera').value=selected;
  el('reprocess').disabled = !status.configured;
  el('diagnostics').textContent = status.diagnostics.map(diagnosticText).join(' | ');
  if (!status.configured) el('message').textContent='Source configuration is required before processing.';
  jobs = await api('jobs');
  el('jobs').replaceChildren(...jobs.map(job=>{
    const row=document.createElement('div'); row.className='job';
    const info=document.createElement('div'), name=document.createElement('strong'), detail=document.createElement('small'), state=document.createElement('span');
    name.textContent=`${job.camera} · ${job.day}`;
    detail.textContent=job.error || `${job.attempts} processing attempt${job.attempts===1?'':'s'}`;
    state.className=`state ${job.status==='failed'?'failed':''}`; state.textContent=job.status;
    info.append(name,detail);
    for (const difference of job.details || []) {
      const line=document.createElement('small');
      line.textContent=`Clip ${difference.clip} vs ${difference.reference_clip}, stream ${difference.stream} · ${difference.field}: ${difference.actual} vs ${difference.expected}`;
      info.append(line);
    }
    row.append(info,state);return row;
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
    el('message').textContent=result.diagnostics.length?`Processing blocked: ${diagnosticText(result.diagnostics[0])}`:result.queued?'Day queued for sequential processing.':'No new job queued; it may already be pending or have no eligible clips.';
    await refresh();
  } catch(e) {el('message').textContent=e.message;} finally {el('reprocess').disabled=false;}
});

let galleryView='latest', galleryDay=null, gallerySignature=null, galleryBusy=false, galleryRevision=0, pendingGallery=false, galleryDates=[];
const initial=new URLSearchParams(location.hash.slice(1));
let embedded=initial.get('embed')==='1';
document.body.classList.toggle('embedded',embedded);
function galleryPlayers(){return [...el('gallery-grid').querySelectorAll('video')];}
function stopGallery(){for(const video of galleryPlayers()){video.closest('.surveillance-player')?.releaseLayout?.();video.pause();video.removeAttribute('src');video.load();}}
function galleryQuery(){const query=new URLSearchParams({view:galleryView});if(galleryView==='day' && galleryDay)query.set('day',galleryDay);return query.toString();}
function selectView(view,day=null,writeHash=true){
  stopGallery();galleryView=['latest','day','manage'].includes(view)?view:'latest';
  if(embedded && galleryView==='manage')galleryView='latest';
  document.body.classList.toggle('surveillance',galleryView!=='manage');
  galleryDay=day;gallerySignature=null;pendingGallery=false;galleryRevision++;
  el('management').hidden=galleryView!=='manage';el('gallery-panel').hidden=galleryView==='manage';
  for(const mode of ['latest','day','manage'])el(`view-${mode}`).setAttribute('aria-pressed',String(galleryView===mode));
  if(writeHash){const hash=new URLSearchParams({view:galleryView});if(embedded)hash.set('embed','1');if(galleryDay)hash.set('day',galleryDay);history.replaceState(null,'','#'+hash);}
  if(galleryView!=='manage')refreshGallery(true);
}
function renderCollection(data){
  stopGallery();el('gallery-grid').replaceChildren();
  el('gallery-title').textContent=galleryView==='latest'?'Latest per camera':`All cameras · ${data.day || 'select a date'}`;
  el('gallery-description').textContent=galleryView==='latest'?'Each camera shows its own most recent published day. Dates can differ.':'All available daily exports for the selected date.';
  const isDay=galleryView==='day';
  for(const id of ['gallery-date-control','gallery-previous','gallery-next'])el(id).hidden=!isDay;
  el('gallery-day').value=data.day || '';
  el('gallery-back').hidden=!(isDay && embedded);
  const position=galleryDates.indexOf(data.day);
  el('gallery-previous').disabled=position<0 || position>=galleryDates.length-1;
  el('gallery-next').disabled=position<=0;
  let available=0;
  for(const item of data.videos){
    const tile=document.createElement('article');tile.className='camera-tile';tile.dataset.camera=item.camera;
    const title=document.createElement('h3');title.textContent=item.camera;
    const day=document.createElement('p');day.className='tile-date';day.textContent=item.day || 'No export yet';
    tile.append(title,day);
    if(item.available){
      available++;
      const video=document.createElement('video');video.controls=false;video.disablePictureInPicture=true;video.preload='none';video.muted=true;video.playsInline=true;video.src=item.video_url;video.setAttribute('aria-label',`${item.camera} · ${item.day}`);
      const warning=document.createElement('p');warning.className='tile-warning';warning.hidden=true;warning.textContent='Playback unavailable. H.265 support varies; try a compatible player or refresh if the export changed.';
      video.addEventListener('error',()=>warning.hidden=false);
      const player=createSurveillancePlayer(video,item.camera);
      player.addEventListener('playback-error',()=>warning.hidden=false);
      const links=document.createElement('div');links.className='tile-links';
      const download=document.createElement('a');download.href=item.download_url;download.textContent='↓';download.title='Download MP4';download.setAttribute('aria-label',`${item.camera}: Download MP4`);download.setAttribute('download','');links.append(download);
      if(galleryView==='latest'){const together=document.createElement('button');together.className='secondary';together.textContent='▦';together.title='All cameras on this day';together.setAttribute('aria-label',`${item.camera}: All cameras on this day`);together.addEventListener('click',()=>selectView('day',item.day));links.append(together);}
      player.querySelector('.video-controls').append(links);
      if(item.previous_export){warning.hidden=false;warning.textContent='Previous successful export; current job '+item.job_status;}
      tile.append(player,warning);
    }else{const empty=document.createElement('p');empty.className='tile-empty';empty.textContent=item.unavailable_reason || (item.job_status?`No completed export · ${item.job_status}`:'No completed export for this camera/date.');tile.append(empty);}
    el('gallery-grid').append(tile);
  }
  if(!data.videos.length){const empty=document.createElement('p');empty.textContent='Configure camera sources to show daily recordings.';el('gallery-grid').append(empty);}
  el('gallery-play').disabled=available===0 || available>6;
  el('gallery-play').title=available>6?'Use individual controls for up to six cameras at a time.':'';
  el('gallery-pause').disabled=available===0;
  el('gallery-message').textContent='';
}
async function refreshGallery(force=false){
  if(galleryBusy || galleryView==='manage')return;
  galleryBusy=true;const revision=galleryRevision;const query=galleryQuery();
  try{
    const data=await api('videos?'+query);
    if(revision!==galleryRevision)return;
    galleryDates=data.dates;
    const signature=JSON.stringify(data.videos);
    if(!force && signature===gallerySignature)return;
    if(!force && galleryPlayers().some(video=>!video.paused && !video.ended)){
      pendingGallery=true;el('gallery-message').textContent='New exports are ready. Pause playback or refresh to load them.';return;
    }
    renderCollection(data);gallerySignature=signature;pendingGallery=false;
  }catch(error){el('gallery-message').textContent=error.message;}
  finally{galleryBusy=false;if(revision!==galleryRevision && galleryView!=='manage')refreshGallery(true);}
}
for(const view of ['latest','day','manage'])el(`view-${view}`).addEventListener('click',()=>selectView(view));
el('gallery-day').addEventListener('change',()=>selectView('day',el('gallery-day').value || null));
el('gallery-previous').addEventListener('click',()=>{const n=galleryDates.indexOf(el('gallery-day').value);if(n>=0 && n+1<galleryDates.length)selectView('day',galleryDates[n+1]);});
el('gallery-next').addEventListener('click',()=>{const n=galleryDates.indexOf(el('gallery-day').value);if(n>0)selectView('day',galleryDates[n-1]);});
el('gallery-refresh').addEventListener('click',()=>refreshGallery(true));
el('gallery-pause').addEventListener('click',()=>{for(const video of galleryPlayers())video.pause();if(pendingGallery)refreshGallery(true);});
el('gallery-play').addEventListener('click',async()=>{
  const results=await Promise.allSettled(galleryPlayers().map(video=>{video.muted=true;return video.play();}));
  if(results.some(result=>result.status==='rejected'))el('gallery-message').textContent='Some videos could not start; use their individual controls or downloads.';
});
selectView(initial.get('view') || 'latest',initial.get('day'),false);
refresh().catch(error=>el('message').textContent=error.message);
setInterval(()=>{if(!document.hidden && galleryView!=='manage')refreshGallery();},60000);

window.addEventListener('hashchange',()=>{const parameters=new URLSearchParams(location.hash.slice(1));embedded=parameters.get('embed')==='1';document.body.classList.toggle('embedded',embedded);selectView(parameters.get('view') || 'latest',parameters.get('day'),false);});

el('gallery-back').addEventListener('click',()=>selectView('latest'));

el('dashboard-help').addEventListener('click',()=>{const setup=document.querySelector('.dashboard-setup');setup.open=true;setup.scrollIntoView({block:'start',behavior:'smooth'});});

// Called only by the same-origin Home Assistant properties bridge.
function nativeDashboardView(view, day) {
  embedded=true;document.body.classList.add('embedded');
  selectView(view,day);
}
