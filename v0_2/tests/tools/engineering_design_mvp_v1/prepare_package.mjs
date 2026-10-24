// Source packaging and static result export only. No local numerical model.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {stable,digest,reportHTML} from './core.mjs';
const root=path.resolve(import.meta.dirname,'../../../..'),here=import.meta.dirname;
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const design=read('v0_2/tests/tools/engineering_design_mvp_v1/data/baseline.json');
const request={schema:'C2C-ENGINEERING-JOB-1',model:'tank90',design_json:stable(design),design_sha256:await digest(design)};
fs.writeFileSync(path.join(here,'request.json'),JSON.stringify(request,null,2));
fs.writeFileSync(path.join(here,'data/baseline_report.html'),reportHTML(design,design,read('v0_2/tests/tools/engineering_design_mvp_v1/data/historical.json')));
const legacy=new Map();
for(const name of ['memphis_single_rack_v1','memphis_equipment_validation_v2']){
 const m=read(`v0_2/tests/tools/${name}/source_manifest.json`);
 for(const [p,h] of Object.entries({...m.v1_source_raw_sha256,...m.source_raw_sha256})){
  if(p.startsWith('.github/'))continue; // Old workflows are not executable dependencies of this task.
  if(hash(p)!==h)throw Error('PROTECTED_SOURCE_DRIFT '+p);
  if(legacy.has(p)&&legacy.get(p)!==h)throw Error('CONFLICTING_LEGACY_IDENTITY '+p);
  legacy.set(p,h);
 }
}
for(const p of ['v0_2/tests/tools/liquid_recovery_v1/batch.ps1','v0_2/tests/tools/memphis_00_01_hydraulic_v1/basis.json'])legacy.set(p,hash(p));
const files=new Map(legacy),prefix='v0_2/tests/tools/engineering_design_mvp_v1/';
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){if(e.name==='__pycache__')continue;const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else{const rel=path.relative(root,p).replaceAll('\\','/');if(!['source_manifest.json','request.json','visual_ci_manifest.json'].includes(e.name))files.set(rel,hash(rel));}}}
walk(here);
for(const p of ['.github/workflows/engineering-design-mvp-v1.yml','.github/workflows/engineering-design-visual-ci.yml','PRODUCT.md','DESIGN.md'])files.set(p,hash(p));
const manifest={schema:'C2C-ENGINEERING-SOURCE-1',scope:'TANK90_OR_SIX60_BOUNDED_RESEARCH_NOT_ENGINEERING_APPROVAL',
 mutable_input:prefix+'request.json',input_binding:'raw request SHA256 and embedded canonical design SHA256; executable source fixed by operator commit',
 frozen_legacy_files:legacy.size,source_files:[...files].sort(([a],[b])=>a.localeCompare(b)).map(([path,sha256])=>({path,sha256}))};
fs.writeFileSync(path.join(here,'source_manifest.json'),JSON.stringify(manifest,null,2));
const visualFiles=[...files].filter(([p])=>p.startsWith(prefix)||['.github/workflows/engineering-design-visual-ci.yml','PRODUCT.md','DESIGN.md'].includes(p));
for(const p of [prefix+'source_manifest.json',prefix+'request.json'])visualFiles.push([p,hash(p)]);
fs.writeFileSync(path.join(here,'visual_ci_manifest.json'),JSON.stringify({schema:'C2C-VISUAL-CI-SOURCE-1',scope:'PRODUCT_AND_SAVED_RECORD_BROWSER_ONLY_NO_NEW_PHYSICS',files:visualFiles.sort(([a],[b])=>a.localeCompare(b)).map(([path,sha256])=>({path,sha256}))},null,2));
console.log(JSON.stringify({source_files:files.size,preserved_legacy:legacy.size,manifest_sha256:hash(prefix+'source_manifest.json'),request_model:request.model,remote_executed:false}));
