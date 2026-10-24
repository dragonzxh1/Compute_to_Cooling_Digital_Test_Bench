// Product/formula/HTTP checks only. Never execute validation.py, native code or a physical model locally.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {spawnSync} from 'node:child_process';
import {edit,compare,reportHTML,digest} from './core.mjs';
import {visualReportHTML} from './visual-ui.mjs';
const here=import.meta.dirname,root=path.resolve(here,'../../../..'),prefix='v0_2/tests/tools/engineering_design_mvp_v1/';
const out=path.join(root,'artifacts/engineering-design-mvp-v1','local-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(out,{recursive:true});
const records=[];
function run(name,exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',timeout:30000,windowsHide:true});fs.writeFileSync(path.join(out,name+'.stdout.txt'),r.stdout||'');fs.writeFileSync(path.join(out,name+'.stderr.txt'),r.stderr||'');const rec={name,exit:r.status,error:r.error?.message||null};records.push(rec);if(r.status!==0)throw Error(name+' failed; evidence preserved in '+out);return r;}
try{
 const js=run('product-core',process.execPath,[prefix+'test_core.mjs']);const checks=JSON.parse(js.stdout).tests;
 const visualChecks=JSON.parse(run('visual-records',process.execPath,[prefix+'test_visual.mjs']).stdout);
 const switchingChecks=JSON.parse(run('switching-records',process.execPath,[prefix+'test_switching.mjs']).stdout);
 const py=run('http-contract','D:/Github/c2c-itq-qualification-r3/Scripts/python.exe',['-B','-m','v0_2.tests.tools.engineering_design_mvp_v1.test_server']);
 run('frontend-syntax',process.execPath,['--check',prefix+'app.mjs']);
 run('visual-core-syntax',process.execPath,['--check',prefix+'visual-core.mjs']);
 run('visual-ui-syntax',process.execPath,['--check',prefix+'visual-ui.mjs']);
 const base=JSON.parse(fs.readFileSync(path.join(here,'data/baseline.json'))),history=JSON.parse(fs.readFileSync(path.join(here,'data/historical.json')));
 const modified=edit(edit(base,'tank_volume',20),'ua',110),rows=compare(base,modified);
 fs.writeFileSync(path.join(out,'tank20-ua110.design.json'),JSON.stringify(modified,null,2));
 fs.writeFileSync(path.join(out,'comparison.json'),JSON.stringify(rows,null,2));
 fs.writeFileSync(path.join(out,'engineering_decision_report.html'),reportHTML(modified,base,history));
 const source=p=>fs.readFileSync(path.join(here,p),'utf8');
 fs.writeFileSync(path.join(out,'visual_replay_report.html'),visualReportHTML({design:base,history,single:JSON.parse(source('data/single_history.json')),switching:JSON.parse(source('data/switching.json')),designHash:await digest(base),coreSource:source('visual-core.mjs'),uiSource:source('visual-ui.mjs'),styles:source('style.css')},{dataset:'single',caseID:'SR_STUCK',t:30,selected:'pump'}));
 fs.writeFileSync(path.join(out,'scenario_comparison_30s.json'),JSON.stringify(visualChecks.actual_at_30s,null,2));
 const result={status:'LOCAL_PRODUCT_SLICE_VALIDATED_REMOTE_DYNAMIC_PENDING',js_tests:checks.length,http_tests:Number(py.stderr.match(/Ran (\d+) tests/)?.[1]),
  design_sha256:await digest(modified),visual_tests:visualChecks.tests.length,switching_tests:switchingChecks.tests.length,scope:'FORMULAS_VERSIONING_TOPOLOGY_CONTRACT_HTTP_HISTORICAL_DISPLAY_ONLY',local_numerical_model_executed:false,remote_executed:false,
  engineering_status:'MEMPHIS_ENGINEERING_NOT_APPROVED',records,
  example:{tank15_to20_cold_volume_m3:rows.find(r=>r.id==='cold'),ua220_to110_capacity_kw:rows.find(r=>r.id==='hx_capacity')},
  remaining:['New dedicated branch publication and remote development testing require explicit task authorization','Remote adapter and official-artifact admission require actual execution','Default topology remains a functional reduction, not full 00/01 construction geometry']};
 fs.writeFileSync(path.join(out,'local_verification.json'),JSON.stringify(result,null,2));
 const files=fs.readdirSync(out).map(p=>({path:p,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,p))).digest('hex')}));
 fs.writeFileSync(path.join(out,'artifact_hashes.json'),JSON.stringify({scope:result.scope,files},null,2));
 console.log(JSON.stringify({output:out,status:result.status,js_tests:result.js_tests,visual_tests:result.visual_tests,switching_tests:result.switching_tests,http_tests:result.http_tests}));
}catch(e){fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({error:e.message,records}));throw e;}
