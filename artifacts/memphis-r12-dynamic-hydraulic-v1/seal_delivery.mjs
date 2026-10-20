// Mechanical delivery hashing, no model execution.
import {readFileSync,writeFileSync,readdirSync,cpSync,mkdirSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
const dir=resolve(process.argv[2]),source=resolve(process.argv[3]);
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const reg=JSON.parse(readFileSync(join(dir,'registration.json'),'utf8'));
mkdirSync(join(dir,'inputs'),{recursive:true});
const input=join(source,'v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1/inputs/pid.expanded.json');
if(sha(input)!==reg.topology_sha256)throw Error('INPUT_IDENTITY');
cpSync(input,join(dir,'inputs/pid.expanded.json'));
cpSync(join(source,'v0_2/tests/tools/memphis_r12_dynamic_hydraulic_v1/inputs/pid_spec.json'),join(dir,'inputs/pid_spec.json'));
const records=[];
function walk(folder,relative=''){
 for(const d of readdirSync(folder,{withFileTypes:true})){
  const path=join(folder,d.name),rel=relative+d.name;
  if(d.isDirectory())walk(path,rel+'/');
  else if(rel!=='delivery_hashes.json')records.push({path:rel,bytes:readFileSync(path).length,sha256:sha(path)});
 }
}
walk(dir);
writeFileSync(join(dir,'delivery_hashes.json'),JSON.stringify({schema:'R12-REVIEWED-DELIVERY-ALL-FILES-1',
 source_commit:'cfc7eb2663f8ed28ea8bfcc3b88182c54983d941',run:'39492934891',
 status:'PARTIAL_DYNAMIC_EVIDENCE_NOT_ENGINEERING_APPROVED',records},null,2)+'\n');
console.log(JSON.stringify({files:records.length,manifest_sha256:sha(join(dir,'delivery_hashes.json'))},null,2));
