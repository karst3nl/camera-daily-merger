'use strict';
// Visual preferences only; no camera data or ingress credentials are persisted.
(() => {
  const key='camera-daily-merger.layout.v1';
  const columns=document.getElementById('layout-columns');
  const size=document.getElementById('layout-size');
  const output=document.getElementById('layout-size-value');
  const grid=document.getElementById('gallery-grid');
  const valid=value=>value && ['auto','1','2','3','4'].includes(value.columns) && Number.isInteger(value.size) && value.size>=50 && value.size<=100 && value.size%5===0;
  let saved;
  try{saved=JSON.parse(localStorage.getItem(key));}catch{/* Private or restricted storage: keep working in memory. */}
  if(valid(saved)){columns.value=saved.columns;size.value=String(saved.size);}
  function apply(persist){
    grid.dataset.columns=columns.value;
    grid.style.width=`${size.value}%`;
    output.value=`${size.value}%`;
    if(persist){
      try{localStorage.setItem(key,JSON.stringify({columns:columns.value,size:Number(size.value)}));document.getElementById('layout-status').textContent='Saved in this browser.';}
      catch{document.getElementById('layout-status').textContent='Browser storage unavailable; applies until this page is closed.';}
    }
  }
  columns.addEventListener('change',()=>apply(true));
  size.addEventListener('input',()=>apply(false));
  size.addEventListener('change',()=>apply(true));
  document.getElementById('layout-reset').addEventListener('click',()=>{columns.value='auto';size.value='100';apply(true);});
  apply(false);
})();
