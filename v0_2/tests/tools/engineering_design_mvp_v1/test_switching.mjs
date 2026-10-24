// Historical display and identity tests only; never run a solver locally.
import fs from 'node:fs';import assert from 'node:assert/strict';
import {atTime,sourceSwitchScene,cduSwitchScene,cduPrimaryFlow} from './visual-core.mjs';
const d=JSON.parse(fs.readFileSync(new URL('./data/switching.json',import.meta.url))),tests=[];
function test(name,fn){fn();tests.push({name,status:'PASS'});}
test('source frames retain original .1s timestamps',()=>{assert.equal(d.source.frames.length,2400);assert.equal(d.source.frames[0].t_s,.1);assert.equal(d.source.frames.at(-1).t_s,240);});
test('source actual path really changes W1 to W2',()=>{assert.equal(atTime(d.source.frames,10).source_path,'W1');assert.equal(atTime(d.source.frames,60).source_path,'W2');});
test('source and load tank selectors are independent actual channels',()=>{const f=atTime(d.source.frames,113);assert.equal(f.source_tank,'A');assert.equal(f.load_tank,'B');});
test('source cut does not borrow command flow',()=>{const sc=sourceSwitchScene(d.source,35);assert.ok(sc.edges.filter(e=>e.id.startsWith('source-')).every(e=>e.q===0));assert.ok(sc.edges.find(e=>e.id==='load-feed').q>0);});
test('selected tower does not animate during zero-flow cold-build',()=>{const sc=sourceSwitchScene(d.source,60);assert.equal(sc.edges.find(e=>e.id==='source-W1').q,0);assert.equal(sc.edges.find(e=>e.id==='source-W2').q,0);});
test('unselected tower does not receive selected-path flow',()=>{const sc=sourceSwitchScene(d.source,100);assert.equal(sc.edges.find(e=>e.id==='source-W1').q,0);assert.ok(sc.edges.find(e=>e.id==='source-W2').q>0);});
test('actual command timestamp never from future',()=>assert.ok(d.source.frames.every(f=>!f.command||f.command.issued_s<=f.t_s)));
const cold=d.cdu_cases.T2_COLD_STANDBY,warm=d.cdu_cases.T2_WARM_STANDBY,loss=d.cdu_cases.NEG_DUTY_PUMP_LOSS;
test('R12 official source identity retained, not current 00/01',()=>{assert.equal(cold.source,'cfc7eb2663f8ed28ea8bfcc3b88182c54983d941');assert.equal(cold.bindings.zip_sha256,'371fa29d99aa97d778a451c20fe98c7450816d320c91e5a55f28e731de613263');});
test('all complete R12 histories retain 600 original POST records',()=>{for(const c of Object.values(d.cdu_cases)){assert.equal(c.frames.length,600);assert.equal(c.frames[0].t_s,.1);assert.equal(c.frames.at(-1).t_s,60);}});
test('six distinct CDU identities exist',()=>{const sc=cduSwitchScene(cold,40);assert.equal(sc.nodes.filter(n=>/^U[123]-CDU-[AB]$/.test(n.id)).length,6);});
test('CDU B uses primary A after takeover, primary B remains closed',()=>{const f=atTime(cold.frames,40);assert.ok(cduPrimaryFlow(f,'B','A')>0);assert.equal(cduPrimaryFlow(f,'B','B'),0);assert.equal(f.master,'B');});
test('actual overlap contains both CDU flow records',()=>{const f=atTime(cold.frames,25);assert.ok(f.cdus.A.secondary_flow_m3_h>0);assert.ok(f.cdus.B.secondary_flow_m3_h>0);});
test('warm standby never fabricates completed takeover',()=>{assert.equal(warm.summary.complete_at,null);assert.notEqual(atTime(warm.frames,60).master,'B');});
test('pump-loss counterexample preserves zero flow',()=>assert.ok(loss.frames.some(f=>f.unit_flow_m3_h===0)));
test('four unmodeled CDU devices retain unknown values and no flow',()=>{const sc=cduSwitchScene(cold,40);for(const u of [2,3]){for(const side of ['A','B']){const n=sc.nodes.find(n=>n.id===`U${u}-CDU-${side}`);assert.equal(n.temperature,undefined);assert.equal(n.operating,false);assert.equal(sc.edges.find(e=>e.id===`P2-U${u}-${side}`).q,null);}}});
test('U2 rack drilldown cannot inherit U1 observations',()=>{const sc=cduSwitchScene(cold,40,2);assert.equal(sc.frame,null);assert.ok(sc.nodes.filter(n=>n.type==='rack').every(n=>n.temperature===undefined));assert.ok(sc.edges.every(e=>e.q===null));});
test('pressure failure retained alongside partial thermal/hydraulic PASS',()=>{assert.equal(cold.summary.hx_pressure_verdict,'FAIL');assert.equal(cold.summary.engineering_status,'MEMPHIS_ENGINEERING_NOT_APPROVED');});
console.log(JSON.stringify({scope:'HISTORICAL_SWITCHING_DISPLAY_ONLY_NOT_NEW_QUALIFICATION',tests},null,2));
