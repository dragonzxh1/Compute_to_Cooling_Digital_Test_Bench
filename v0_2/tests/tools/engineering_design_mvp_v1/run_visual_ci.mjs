// GitHub-only product/browser verification. No numerical model imports or calls.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {spawn,spawnSync} from 'node:child_process';import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
if(process.env.GITHUB_ACTIONS!=='true')throw Error('GITHUB_ONLY: do not run this test driver on the user machine');
const here=import.meta.dirname,root=path.resolve(here,'../../../..'),out=path.join(root,'artifacts/engineering-design-visual-ci');
fs.mkdirSync(out,{recursive:true});
const records=[],save=(name,value)=>fs.writeFileSync(path.join(out,name),typeof value==='string'?value:JSON.stringify(value,null,2));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const result={scope:'PRODUCT_AND_SAVED_RECORD_BROWSER_TESTS_ONLY',commit:process.env.GITHUB_SHA,run:process.env.GITHUB_RUN_ID,local_model_executed:false,new_physical_simulation:false,engineering_status:'MEMPHIS_ENGINEERING_NOT_APPROVED',records};
let server,browser;
function run(name,exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',timeout:45000});save(name+'.stdout.txt',r.stdout||'');save(name+'.stderr.txt',r.stderr||'');records.push({name,exit:r.status,error:r.error?.message});if(r.status!==0)throw Error(name+' failed');return r;}
async function acceptance(page,file,key,name){await page.evaluate(fs.readFileSync(path.join(here,file),'utf8'));const raw=await page.evaluate(async k=>await window[k],key),r=typeof raw==='string'?JSON.parse(raw):raw;save(name+'.json',r);records.push({name,checks:r.checks.length,failures:r.checks.filter(x=>x.status!=='PASS')});if(r.checks.some(x=>x.status!=='PASS'))throw Error(name+' failed');}
try{
 const manifest=JSON.parse(fs.readFileSync(path.join(here,'visual_ci_manifest.json')));
 for(const f of manifest.files){if(sha(fs.readFileSync(path.join(root,f.path)))!==f.sha256)throw Error('SOURCE_DRIFT '+f.path);}
 save('source_identity.json',{commit:result.commit,manifest_sha256:sha(fs.readFileSync(path.join(here,'visual_ci_manifest.json'))),files:manifest.files});
 run('node-version',process.execPath,['--version']);run('python-version','python',['--version']);
 for(const file of ['test_core.mjs','test_visual.mjs','test_switching.mjs'])run(file,process.execPath,[path.join(here,file)]);
 run('http-contract','python',['-B','-m','v0_2.tests.tools.engineering_design_mvp_v1.test_server']);
 for(const file of ['app.mjs','visual-core.mjs','visual-ui.mjs'])run('syntax-'+file,process.execPath,['--check',path.join(here,file)]);
 const log=fs.openSync(path.join(out,'http-server.log'),'w');
 server=spawn('python',['-B','-m','v0_2.tests.tools.engineering_design_mvp_v1.server','--port','8768'],{cwd:root,stdio:['ignore',log,log]});fs.closeSync(log);
 let ready=false;for(let i=0;i<50;i++){try{const r=await fetch('http://127.0.0.1:8768/api/catalog');if(r.ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready)throw Error('HTTP_SERVER_NOT_READY');
 const require=createRequire(path.join(process.env.C2C_UI_DEPS,'package.json')),{chromium}=require('playwright');
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1600,height:1000},deviceScaleFactor:1}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const open=async()=>{await page.goto('http://127.0.0.1:8768/');await page.waitForSelector('#v-dataset');};
 await open();await page.screenshot({path:path.join(out,'default-replay-entry.png'),fullPage:true});await acceptance(page,'browser_entry_acceptance.js','c2cEntryPromise','browser-dynamic-entry');
 await open();await acceptance(page,'browser_acceptance.js','c2cVisualAcceptancePromise','browser-regression');
 await open();await acceptance(page,'browser_switching_acceptance.js','c2cSwitchingPromise','browser-switching');
 await page.selectOption('#v-dataset','source');await page.locator('#v-time').fill('100');await page.screenshot({path:path.join(out,'source-switch.png'),fullPage:true});
 await page.selectOption('#v-dataset','cdu');await page.locator('#v-time').fill('40');await page.screenshot({path:path.join(out,'six-cdu.png'),fullPage:true});
 await page.selectOption('#v-unit','1');await page.screenshot({path:path.join(out,'unit1-takeover.png'),fullPage:true});
 const download=page.waitForEvent('download');await page.click('#v-export');const exported=await download;const offline=path.join(out,'switching-replay.html');await exported.saveAs(offline);
 await page.goto(pathToFileURL(offline).href);await page.waitForSelector('#v-dataset');
 const offlineChecks=[];const check=(name,ok)=>{offlineChecks.push({name,status:ok?'PASS':'FAIL'});if(!ok)throw Error(name);};
 check('offline preserves CDU dataset',await page.locator('#v-dataset').inputValue()==='cdu');
 check('offline keeps six actual U1 racks',await page.locator('.equipment[data-entity^="rack-"]').count()===6);
 await page.selectOption('#v-dataset','source');await page.locator('#v-time').fill('100');check('offline W2 flow retained',await page.locator('[data-entity="source-W2"] .flow-direction').count()===1);
 await page.selectOption('#v-dataset','cdu');await page.locator('#v-time').fill('40');check('offline six identities retained',await page.locator('.equipment[data-entity*="-CDU-"]').count()===6);
 await page.selectOption('#v-unit','2');check('offline unknown unit stays without flow',await page.locator('.flow-direction').count()===0);
 await page.setViewportSize({width:390,height:844});check('narrow layout has no horizontal body overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(out,'narrow-offline.png'),fullPage:true});save('offline-browser.json',{checks:offlineChecks});
 check('no browser script errors',errors.length===0);save('browser-errors.json',errors);
 result.status='SAVED_SWITCHING_UI_VALIDATED';
}catch(e){result.status='FAIL';result.error=e.stack;process.exitCode=1;}
finally{
 if(browser)await browser.close();
 if(server){const exited=new Promise(r=>server.once('exit',r));server.kill('SIGTERM');await Promise.race([exited,new Promise(r=>setTimeout(r,2000))]);result.server_cleanup_complete=server.exitCode!==null||server.signalCode!==null;}
 save('review_result.json',result);
 const files=fs.readdirSync(out).filter(p=>fs.statSync(path.join(out,p)).isFile()).map(p=>({path:p,sha256:sha(fs.readFileSync(path.join(out,p)))}));save('artifact_hashes.json',{commit:result.commit,run:result.run,files});
 console.log(JSON.stringify({status:result.status,error:result.error,output:out}));
}
