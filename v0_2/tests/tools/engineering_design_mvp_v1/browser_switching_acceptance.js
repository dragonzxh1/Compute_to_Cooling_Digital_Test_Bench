// gstack browse eval only. Actual UI checks of saved records; no new model runs.
window.c2cSwitchingPromise=(async()=>{
 const $=s=>document.querySelector(s),checks=[];
 const check=(name,ok,detail={})=>{checks.push({name,status:ok?'PASS':'FAIL',...detail});if(!ok)throw Error(name);};
 const settle=()=>new Promise(r=>setTimeout(r,100));
 const select=async(s,v)=>{$(s).value=v;$(s).dispatchEvent(new Event('change',{bubbles:true}));await settle();};
 const seek=async t=>{$('#v-time').value=t;$('#v-time').dispatchEvent(new Event('input',{bubbles:true}));await settle();};
 const pick=async id=>{$(`[data-entity="${id}"]`).dispatchEvent(new MouseEvent('click',{bubbles:true}));await settle();};
 const moving=id=>!!$(`[data-entity="${id}"] .flow-direction`);
 const metric=label=>[...$('#v-inspector').querySelectorAll('dl>div')].find(e=>e.querySelector('dt').textContent===label)?.querySelector('dd').textContent.trim();
 try{
  await select('#v-dataset','source');await seek(10);
  check('source uses historical identity',$('#v-origin').textContent.includes('39088951176')&&$('#v-origin').textContent.includes('非当前方案'));
  check('W1 actual flow before failure',moving('source-W1')&&!moving('source-W2'));
  await seek(35);check('zero source flow never animates while load still flows',!moving('source-W1')&&!moving('source-W2')&&moving('load-feed'));
  await seek(60);check('selected W2 can still have no actual flow',$('[data-entity="W2"] .equipment-state').textContent==='实际选中'&&!moving('source-W2'));
  await seek(100);check('actual flow migrates to W2',moving('source-W2')&&!moving('source-W1'));
  await pick('source-pumps');check('actual flow feedback is numeric',parseFloat(metric('实际流量'))>0);
  $('[data-switch-time="112.7"]').click();await settle();check('physical tank event locates exact saved timestamp',Number($('#v-time').value)===112.7);
  await seek(113);check('source and load tank selectors remain independent',$('[data-entity="tank-A"] .equipment-state').textContent==='源侧选中'&&$('[data-entity="tank-B"] .equipment-state').textContent==='负荷侧选中');
  $('[data-entity="tank-B"]').dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));await settle();check('tank drilldown retains actual layer temperatures',$('#v-level').value==='tanks'&&document.querySelectorAll('[data-layer-index]').length===40);
  await select('#v-dataset','cdu');await seek(25);
  check('six distinct CDU devices visible',document.querySelectorAll('.equipment[data-entity*="-CDU-"]').length===6);
  check('both CDU real flows visible during overlap',moving('P2-U1-A')&&moving('P2-U1-B'));
  await seek(40);check('B active after A stops',!moving('P2-U1-A')&&moving('P2-U1-B'));
  check('B receives primary A without primary B flow',moving('P1-B-A')&&!moving('P1-B-B'));
  await pick('U1-CDU-B');check('pressure master is separately visible',$('#v-inspector').textContent.includes('U1实际压力主站：B'));
  check('other four CDU devices remain unknown',[2,3].every(u=>['A','B'].every(s=>!$(`[data-entity="U${u}-CDU-${s}"]`).classList.contains('operating')&&!moving(`P2-U${u}-${s}`))));
  await select('#v-unit','2');check('U2 does not borrow U1 curves or flows',document.querySelectorAll('.flow-direction').length===0&&$('#v-curves').textContent.includes('没有动态记录')&&document.querySelectorAll('.equipment[data-entity^="rack-"]').length===6);
  $('#v-up').click();await settle();check('return to overview restores six devices',document.querySelectorAll('.equipment[data-entity*="-CDU-"]').length===6);
  await select('#v-unit','1');check('U1 per-rack feedback comes from actual records',document.querySelectorAll('.equipment[data-entity^="rack-"]').length===6&&moving('rack-B-1'));
  $('[data-cdu-case="T2_WARM_STANDBY"]').click();await settle();await seek(60);await pick('U1-CDU-B');
  check('warm standby does not force handover',!$('[data-entity="U1-CDU-B"]').classList.contains('operating')&&$('#v-inspector').textContent.includes('PREPARE_B'));
  $('[data-cdu-case="NEG_DUTY_PUMP_LOSS"]').click();await settle();await seek(40);check('loss-of-flow negative case stops secondary branches while primary can circulate',![...document.querySelectorAll('.pipe-entity[data-entity^="rack-"]')].some(e=>e.querySelector('.flow-direction'))&&moving('P1-A-A'));
  $('[data-cdu-case="T2_COLD_STANDBY"]').click();await settle();await seek(60);await pick('U1-CDU-B');
  check('historical pressure FAIL remains disclosed',$('#v-inspector').textContent.includes('HX入口跨侧压力 FAIL'));
  check('no page horizontal overflow',document.documentElement.scrollWidth<=innerWidth,{width:innerWidth,scroll_width:document.documentElement.scrollWidth});
 }catch(e){checks.push({name:'unexpected error',status:'FAIL',error:e.message});}
 window.c2cSwitchingAcceptance={scope:'ACTUAL_BROWSER_SAVED_SWITCHING_ONLY_NO_NEW_SIMULATION',checks};
 return JSON.stringify(window.c2cSwitchingAcceptance,null,2);
})()
