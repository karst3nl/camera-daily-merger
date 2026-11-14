'use strict';
(() => {
  // Default existing installations to the requested fixed two-column automatic wall.
  const key='camera-daily-merger.layout.v3';
  const columns=document.getElementById('layout-columns');
  const size=document.getElementById('layout-size');
  const output=document.getElementById('layout-size-value');
  const grid=document.getElementById('gallery-grid');
  const status=document.getElementById('layout-status');
  const valid=value=>value && ['auto','1','2','3','4'].includes(value.columns) && Number.isInteger(value.size) && value.size>=50 && value.size<=100 && value.size%5===0;
  let saved,queued=false,storageBlocked=false;
  try{saved=JSON.parse(localStorage.getItem(key));}catch{storageBlocked=true;}
  if(valid(saved)){columns.value=saved.columns;size.value=String(saved.size);}
  function fit(){
    queued=false;
    const automatic=columns.value==='auto';
    const active=automatic && document.body.classList.contains('surveillance');
    document.body.classList.toggle('auto-fit',active);
    size.disabled=automatic;
    output.value=automatic?'Automatic':`${size.value}%`;
    grid.dataset.columns=columns.value;
    grid.style.removeProperty('grid-template-columns');
    grid.style.removeProperty('grid-template-rows');
    grid.style.removeProperty('height');
    grid.style.width=automatic?'100%':`${size.value}%`;
    if(!active || document.getElementById('gallery-panel').hidden)return;
    if(document.fullscreenElement)return;
    const count=grid.querySelectorAll('.camera-tile').length;
    if(!count)return;
    const main=document.querySelector('main');
    const padding=parseFloat(getComputedStyle(main).paddingBottom)||0;
    // The app/card viewport bounds the complete two-column camera wall.
    const viewport=window.visualViewport;
    const bottom=(viewport?viewport.height:innerHeight)-padding-2;
    const top=grid.getBoundingClientRect().top+window.scrollY;
    const height=Math.max(0,Math.floor(bottom-top));
    const fitColumns=Math.min(2,count),rows=Math.ceil(count/fitColumns);
    grid.style.height=`${height}px`;
    grid.style.gridTemplateColumns=`repeat(${fitColumns},minmax(0,1fr))`;
    grid.style.gridTemplateRows=`repeat(${rows},minmax(0,1fr))`;
    grid.dataset.fitColumns=String(fitColumns);
    grid.dataset.fitRows=String(rows);
    grid.dataset.fitViewportWidth=String(innerWidth);
    grid.dataset.fitViewportHeight=String(innerHeight);
    const message=`Automatic: ${fitColumns} × ${rows}.`;
    status.textContent=message+(storageBlocked?' Browser storage unavailable.':'');
  }
  function schedule(){if(!queued){queued=true;requestAnimationFrame(fit);}}
  function apply(persist){
    if(persist){
      try{localStorage.setItem(key,JSON.stringify({columns:columns.value,size:Number(size.value)}));storageBlocked=false;status.textContent='Saved in this browser.';}
      catch{storageBlocked=true;status.textContent='Browser storage unavailable; applies until this page is closed.';}
    }
    fit();
  }
  columns.addEventListener('change',()=>apply(true));
  size.addEventListener('input',()=>apply(false));
  size.addEventListener('change',()=>apply(true));
  document.getElementById('layout-reset').addEventListener('click',()=>{columns.value='auto';size.value='100';apply(true);});
  const resize=new ResizeObserver(schedule);
  for(const node of document.querySelectorAll('.view-tabs,.gallery-controls,.layout-settings,#gallery-message,.gallery-panel>.section-title'))resize.observe(node);
  new MutationObserver(schedule).observe(grid,{childList:true});
  new MutationObserver(schedule).observe(document.body,{attributes:true,attributeFilter:['class']});
  grid.addEventListener('error',schedule,true);
  window.addEventListener('resize',schedule);
  window.visualViewport?.addEventListener('resize',schedule);
  document.addEventListener('fullscreenchange',schedule);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule();});
  document.fonts?.ready.then(schedule);
  apply(false);
})();
