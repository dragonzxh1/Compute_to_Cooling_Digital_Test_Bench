// Run only with gstack browse eval against the local workbench.
// UI actions and read-only assertions; preserves the user's saved draft.
window.c2cVisualAcceptancePromise=(async()=>{
 const $=s=>document.querySelector(s),checks=[];
 const check=(name,condition,detail={})=>{checks.push({name,status:condition?'PASS':'FAIL',...detail});if(!condition)throw Error(name);};
 const settle=()=>new Promise(resolve=>setTimeout(resolve,80));
 const select=async(s,v)=>{$(s).value=v;$(s).dispatchEvent(new Event('change',{bubbles:true}));await settle();};
 const seek=async t=>{$('#v-time').value=t;$('#v-time').dispatchEvent(new Event('input',{bubbles:true}));await settle();};
 const readMetric=label=>[...$('#v-inspector').querySelectorAll('dl>div')].find(d=>d.querySelector('dt').textContent===label)?.querySelector('dd').textContent;
 const original=localStorage.getItem('c2c-design-mvp-draft');
 try{
  await select('#v-dataset','single');await seek(30);
  $('[data-case=SR_STEP]').click();await settle();const step=readMetric('回路流量');
  $('[data-case=SR_STUCK]').click();await settle();const stuck=readMetric('回路流量');
  check('scene change synchronizes actual flow',step!==stuck,{step,stuck});
  check('command/actual remain distinct',readMetric('模拟 PLC 命令')!==readMetric('实际/观测转速'));
  check('saved confirmed fault/latch visible',$('.control-chain').textContent.includes('已锁存'));
  await seek(0);check('future hidden: no confirmed fault at t0',!$('#v-events').textContent.includes('故障已确认'));
  $('#v-play').click();await new Promise(r=>setTimeout(r,500));$('#v-play').click();check('play advances shared clock',Number($('#v-time').value)>0);
  const pause=Number($('#v-time').value);await new Promise(r=>setTimeout(r,200));check('pause fixes shared cursor',Number($('#v-time').value)===pause);
  $('[data-case=SR_MISSING]').click();await settle();await seek(30);await select('#v-layer','arrived');
  check('invalid arrival shows unknown and no moving path',readMetric('回路流量').includes('未知')&&document.querySelectorAll('.flow-direction').length===0);
  check('missing observation is not falsely labeled pump fault',document.querySelectorAll('[data-entity=pump].fault').length===0);
  await select('#v-dataset','ab');await seek(150);
  check('two actual 20-layer records',document.querySelectorAll('[data-layer]').length===40);
  const a150=$('[data-entity=tank-A] .node-value').textContent;await seek(50);check('layer view responds to shared time',a150!==$('[data-entity=tank-A] .node-value').textContent);
  check('future hidden: full-run peak not disclosed',!$('#v-inspector').textContent.includes('46.793'));
  await select('#v-dataset','design');
  const unit=$('[data-entity=U1]');unit.dispatchEvent(new MouseEvent('click',{bubbles:true}));await settle();
  check('equipment selection preserves double-click and keyboard target',unit.isConnected);
  unit.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));await settle();
  check('unit drilldown changes graph layer',$('#v-level').value==='six');
  const standby=$('[data-entity="U1-CDU-B"]');standby.dispatchEvent(new MouseEvent('click',{bubbles:true}));standby.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));await settle();
  check('standby CDU drilldown preserves B identity',$('#v-breadcrumb').textContent.includes('U1-CDU-B'));
  await select('#v-level','six');
  check('six-rack layer shows six distinct cabinets',document.querySelectorAll('[data-entity^=rack-]').length===6);
  check('no fixed primary-B to CDU-B assertion',document.querySelectorAll('.pipe-entity').length===0);
  await select('#v-level','cdu');check('CDU graph uses registered edges',document.querySelectorAll('.pipe-entity').length>=3);
  await select('#v-level','system');$('[data-entity=tank-A]').dispatchEvent(new MouseEvent('click',{bubbles:true}));await settle();
  const input=$('[data-visual-param=tank_volume]'),before=Number(input.value);input.value=before+1;input.dispatchEvent(new Event('change',{bubbles:true}));await settle();await settle();
  check('versioned parameter edit updates graph design value',$('[data-entity=tank-A]').textContent.includes(String(before+1)));
  await select('#v-dataset','current');check('no historical dynamics inherited',document.querySelectorAll('.flow-direction').length===0&&$('#v-scope').textContent.includes('没有输入身份匹配'));
  const w=document.documentElement.scrollWidth;check('no horizontal body overflow',w<=innerWidth,{width:innerWidth,scroll_width:w});
 }catch(e){checks.push({name:'unexpected error',status:'FAIL',error:e.message});}
 finally{if(original===null)localStorage.removeItem('c2c-design-mvp-draft');else localStorage.setItem('c2c-design-mvp-draft',original);}
 window.c2cVisualAcceptance=checks;
 return JSON.stringify({scope:'ACTUAL_BROWSER_UI_ONLY_NO_NEW_SIMULATION',checks},null,2);
})()
