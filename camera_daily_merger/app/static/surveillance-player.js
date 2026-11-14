'use strict';
// Browser-only controls: the video image never carries a native control overlay.
function createSurveillancePlayer(video, camera) {
  const shell=document.createElement('div');shell.className='surveillance-player';
  const viewport=document.createElement('div');viewport.className='video-viewport';
  viewport.append(video);
  const controls=document.createElement('div');controls.className='video-controls';
  controls.setAttribute('role','group');controls.setAttribute('aria-label',`${camera} playback controls`);
  const button=(label,text,action)=>{const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=text;b.title=label;b.setAttribute('aria-label',`${camera}: ${label}`);b.addEventListener('click',action);controls.append(b);return b;};
  const play=button('Play','▶',async()=>{try{if(video.paused)await video.play();else video.pause();}catch{shell.dispatchEvent(new Event('playback-error'));}});
  const updatePlay=()=>{play.textContent=video.paused?'▶':'Ⅱ';play.setAttribute('aria-label',`${camera}: ${video.paused?'Play':'Pause'}`);play.title=video.paused?'Play':'Pause';};
  for(const event of ['play','pause','ended'])video.addEventListener(event,updatePlay);
  const seek=document.createElement('input');seek.type='range';seek.className='video-seek';seek.min='0';seek.max='1';seek.step='0.1';seek.value='0';seek.disabled=true;seek.setAttribute('aria-label',`${camera}: Seek`);controls.append(seek);
  const clock=document.createElement('output');clock.className='video-clock';clock.textContent='00:00';controls.append(clock);
  const updateTime=()=>{const duration=video.duration;seek.disabled=!Number.isFinite(duration)||duration<=0;if(!seek.disabled){seek.max=String(duration);seek.value=String(video.currentTime);}const seconds=Math.floor(video.currentTime||0);clock.textContent=`${Math.floor(seconds/60).toString().padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;};
  for(const event of ['loadedmetadata','timeupdate','durationchange'])video.addEventListener(event,updateTime);
  seek.addEventListener('input',()=>{if(Number.isFinite(video.duration))video.currentTime=Number(seek.value);});
  const sound=button('Unmute','♪',()=>{video.muted=!video.muted;});
  const updateSound=()=>{sound.setAttribute('aria-label',`${camera}: ${video.muted?'Unmute':'Mute'}`);sound.setAttribute('aria-pressed',String(!video.muted));sound.title=video.muted?'Unmute':'Mute';};
  video.addEventListener('volumechange',updateSound);updateSound();
  let zoom=1,x=0,y=0,drag=null;
  const apply=()=>{const limitX=viewport.clientWidth*(zoom-1)/2,limitY=viewport.clientHeight*(zoom-1)/2;x=Math.max(-limitX,Math.min(limitX,x));y=Math.max(-limitY,Math.min(limitY,y));video.style.transform=`translate(${x}px, ${y}px) scale(${zoom})`;viewport.classList.toggle('zoomed',zoom>1);zoomIn.disabled=zoom>=4;zoomOut.disabled=zoom<=1;reset.textContent=`${zoom}×`;};
  const zoomOut=button('Zoom out','−',()=>{zoom=Math.max(1,zoom-0.5);apply();});
  const reset=button('Reset zoom','1×',()=>{zoom=1;x=0;y=0;apply();});
  const zoomIn=button('Zoom in','+',()=>{zoom=Math.min(4,zoom+0.5);apply();});
  viewport.addEventListener('pointerdown',e=>{if(zoom<=1 || (e.pointerType==='mouse' && e.button!==0))return;drag={id:e.pointerId,x:e.clientX,y:e.clientY,baseX:x,baseY:y};viewport.setPointerCapture(e.pointerId);});
  viewport.addEventListener('pointermove',e=>{if(!drag || drag.id!==e.pointerId)return;x=drag.baseX+e.clientX-drag.x;y=drag.baseY+e.clientY-drag.y;apply();});
  for(const event of ['pointerup','pointercancel','lostpointercapture'])viewport.addEventListener(event,()=>{drag=null;});
  if(document.fullscreenEnabled)button('Fullscreen','⛶',async()=>{try{if(document.fullscreenElement===shell)await document.exitFullscreen();else await shell.requestFullscreen();}catch{/* Embedded browser may deny fullscreen. */}});
  shell.addEventListener('fullscreenchange',apply);
  shell.append(viewport,controls);
  const resize=new ResizeObserver(apply);resize.observe(viewport);
  shell.releaseLayout=()=>resize.disconnect();
  apply();return shell;
}
