// Executes only as a child of the externally verified remote Python Job.
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {projectDefaults,assessInputs,primaryRates,towerRating,towerCapacity} from './upstream/model.mjs';
import {validatePackage,canonicalPower,recompute} from './upstream/parameters.mjs';
if(process.env.GITHUB_ACTIONS!=='true'||!process.env.MEMPHIS_VERIFIED_PARENT_PID||process.ppid!==Number(process.env.MEMPHIS_VERIFIED_PARENT_PID))throw Error('VERIFIED_REMOTE_PARENT_REQUIRED');
const directory=process.argv[2];
fs.writeFileSync(directory+'/node_ready.json',JSON.stringify({pid:process.pid,executable:process.execPath}),{flag:'wx'});
const deadline=Date.now()+25000;
while(!fs.existsSync(directory+'/node_release.json')){
 if(Date.now()>deadline)throw Error('NODE_EXTERNAL_JOB_RELEASE_TIMEOUT');
 await new Promise(r=>setTimeout(r,50));
}
const p=JSON.parse(fs.readFileSync(new URL('./upstream/project.json',import.meta.url)));
const c=projectDefaults(p,'HOT'),requirements=assessInputs(c);
const vectors=[];
for(const N of [4,20,40])for(const load of [0,.09166666666666666])for(const source of [0,.06,.09166666666666666,.12]){
 const temps=Array.from({length:N},(_,i)=>40+8*i/(N-1)),x=structuredClone(c);x.primary_flow_m3_s=load;x.tank.mixing_m3_s=.001;
 vectors.push({N,load,source,temps,returnHot:49,sourceCold:39,mixing:.001,rates:primaryRates(x,temps,49,39,source)});
}
const tower=[];
for(const flow of [.02,.06,.09166666666666666,.12])for(const hot of [41,48.29,55]){
 const x=structuredClone(c);x.primary_flow_m3_s=flow;const ratings=towerRating(c);
 tower.push({flow,hot,ratings,capacity:towerCapacity(x,hot,ratings,2716151)});
}
console.log(JSON.stringify({node:{pid:process.pid,parent_pid:process.ppid,version:process.version,executable:process.execPath},
 structure:validatePackage(p),power:canonicalPower(p,{quantity:'IT_ELECTRICAL_POWER',unit:'W',scope:'GROUP18',rack_count:18,value:2790000,basis:'CUSTOMER_DESIGN'}),
 requirements,design:recompute(p),vectors,tower,meaning:'Existing source-bound project functions, not manufacturer performance or physical qualification'}));
