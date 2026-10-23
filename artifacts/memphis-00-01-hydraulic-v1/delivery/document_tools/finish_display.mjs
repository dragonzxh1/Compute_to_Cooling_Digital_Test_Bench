// Display precision only: preserve signed raw CSV/NDJSON values unchanged.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const pkg='D:/Github/c2c-evidence-review/memphis-00-01-hydraulic-v1/run39912648335/reviewed-delivery';
const file=path.join(pkg,'15_INTERACTIVE_REPORT.html'),text=fs.readFileSync(file,'utf8');
const old="document.getElementById('flow').textContent=r.unit_flow_m3_h.toFixed(3)";
if(text.split(old).length!==2)throw Error('DISPLAY_ANCHOR');
const changed=text.replace(old,"document.getElementById('flow').textContent=Math.abs(r.unit_flow_m3_h)<1e-6?'≈0.000':r.unit_flow_m3_h.toFixed(3)")
 .replace('全部数值由对应原始NDJSON生成；','小于10⁻⁶ m³/h仅显示为≈0；原始微小有符号残差保留。全部数值由对应原始NDJSON生成；');
fs.writeFileSync(file,changed);
const manifest=path.join(pkg,'16_SOURCE_AND_EVIDENCE_MANIFEST.json'),m=JSON.parse(fs.readFileSync(manifest));
const r=m.records.find(r=>r.path==='15_INTERACTIVE_REPORT.html');r.bytes=fs.statSync(file).size;r.sha256=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
fs.writeFileSync(manifest,JSON.stringify(m,null,2));
for(const name of ['15_INTERACTIVE_REPORT.html','16_SOURCE_AND_EVIDENCE_MANIFEST.json'])fs.copyFileSync(path.join(pkg,name),path.join('D:/Github/Compute_to_Cooling_Digital_Test_Bench/artifacts/memphis-00-01-hydraulic-v1/reviewed-delivery',name));
console.log(crypto.createHash('sha256').update(fs.readFileSync(manifest)).digest('hex'));
