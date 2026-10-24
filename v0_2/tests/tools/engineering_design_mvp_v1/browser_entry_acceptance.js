// Executed by GitHub browser runner only, no numerical model.
window.c2cEntryPromise=(async()=>{
 const $=s=>document.querySelector(s),checks=[];
 const check=(name,ok)=>{checks.push({name,status:ok?'PASS':'FAIL'});if(!ok)throw Error(name);};
 const wait=ms=>new Promise(r=>setTimeout(r,ms)),choose=async id=>{$(`[data-visual-view="${id}"]`).click();await wait(100);};
 try{
  check('fresh landing opens saved dynamic replay, not static design',$('#v-dataset').value==='source'&&$('#v-mode-title').textContent.includes('仿真回放'));
  check('all five graphical entries are exposed',document.querySelectorAll('[data-visual-view]').length===5);
  check('historical applicability visible before playback',$('#v-mode-detail').textContent.includes('不代表当前00/01'));
  check('primary playback control is visible above graph',$('#v-play-top').getBoundingClientRect().top<$('#v-stage').getBoundingClientRect().top&&!$('#v-play-top').disabled);
  const t=Number($('#v-time').value);$('#v-play-top').click();await wait(600);$('#v-play-top').click();
  check('top play actually advances shared dynamic clock',Number($('#v-time').value)>t);
  check('top pause synchronizes lower control',$('#v-play').textContent==='播放'&&$('#v-play-state').textContent.includes('已暂停'));
  const paused=Number($('#v-time').value);await wait(200);check('pause fixes dynamic clock',Number($('#v-time').value)===paused);
  await choose('cdu');check('CDU entry directly exposes six equipment symbols',document.querySelectorAll('.equipment[data-entity*="-CDU-"]').length===6&&$('#v-dataset').value==='cdu');
  await choose('ab');check('tank entry directly exposes actual layer data',document.querySelectorAll('[data-layer-index]').length===40);
  await choose('single');check('single-rack entry opens physical history',$('#v-dataset').value==='single'&&!$('#v-play-top').disabled);
  await choose('design');check('static design remains explicit and non-playing',$('#v-mode-title').textContent.includes('静态')&&$('#v-play-top').disabled&&document.querySelectorAll('.flow-direction').length===0);
  await choose('source');check('quick tab and dataset remain synchronized',$('[data-visual-view="source"]').getAttribute('aria-pressed')==='true'&&$('#v-dataset').value==='source');
 }catch(e){checks.push({name:'unexpected error',status:'FAIL',error:e.message});}
 return JSON.stringify({scope:'DYNAMIC_REPLAY_ENTRY_BROWSER_ONLY_NO_NEW_PHYSICS',checks},null,2);
})()
