// Assemble already-saved remote evidence and documents; NEVER executes a model.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const root='D:/Github/c2c-evidence-review/memphis-00-01-hydraulic-v1',run='39912648335';
const pkg=path.join(root,'run'+run,'reviewed-delivery');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const write=(p,v)=>fs.writeFileSync(p,typeof v==='string'?v:JSON.stringify(v,null,2),{flag:'wx'});
const review=read(path.join(pkg,'independent_byte_review.json')),stage=review.stages[0];
const raw=path.join(review.official_root,`artifacts/memphis-00-01-hydraulic-v1/${run}-1`);
const evidence=path.join(pkg,'evidence');fs.mkdirSync(evidence);
fs.cpSync(path.join(raw,'baseline'),path.join(evidence,'baseline'),{recursive:true});
fs.cpSync(path.join(raw,'build'),path.join(evidence,'build'),{recursive:true});
fs.copyFileSync(path.join(raw,'host_preflight.json'),path.join(evidence,'host_preflight.json'));
for(const f of ['github_run.json','github_artifacts.json','official_logs.zip'])fs.copyFileSync(path.join(root,'run'+run,f),path.join(evidence,f));
const failures=[];
for(const [id,commit,reason,started] of [
 ['39909757507','7204410221fb161ae70858e8d20b5234098a4b67','IMAGE_DRIFT_NEW_IMAGE_NOT_REGISTERED',true],
 ['39911963438','0aec52a4a836ff42e44e03ce8507945c727742cf','ROLLING_HOST_OLDER_IMAGE_NOT_IN_BUILD002',false],
 ['39912320956','0dd48316022ed1121d1dd94292a0c1080a5865ee','VERIFIER_ARGUMENT_GUARD_STILL_CPU2500',true]]){
 const dir=path.join(root,'run'+id),arts=read(path.join(dir,'github_artifacts.json'));
 const zip=path.join(dir,arts.artifacts[0].name+'.zip'),logs=path.join(dir,'official_logs.zip');
 if('sha256:'+hash(zip)!==arts.artifacts[0].digest)throw Error('FAILED_ZIP_DRIFT');
 const dst=path.join(evidence,'failed-run'+id);fs.mkdirSync(dst);
 for(const f of ['github_run.json','github_artifacts.json','official_logs.zip'])fs.copyFileSync(path.join(dir,f),path.join(dst,f));
 fs.copyFileSync(zip,path.join(dst,path.basename(zip)));
 failures.push({run:id,commit,reason,python_started:started,model_started:false,official_zip_sha256:hash(zip),logs_sha256:hash(logs),verdict:'FAILED_EXECUTION_NOT_PHYSICAL_MODEL_FAIL'});
}
write(path.join(pkg,'retained_failures.json'),failures);
const beats=fs.readdirSync(path.join(raw,'baseline')).filter(n=>n.includes('.heartbeat-')).map(n=>read(path.join(raw,'baseline',n)));
const resources={policy:review.policy,host:review.host_preflight,elapsed_model_s:stage.result.elapsed_s,
 actual_python_pid:stage.actual_python_pid,native:stage.job,raw_files_verified:stage.raw_files_verified,
 sampled_peak_job_memory_MiB:Math.max(...beats.map(b=>b.peak_job_memory_bytes/1048576)),
 memory_note:'Sampled cumulative peak at heartbeat, not guaranteed final peak; no memory pressure benchmark',
 cpu_note:'10000 is allowed CPU rate, NOT measured utilization or a claim of speedup; BLAS remains single-threaded'};
write(path.join(pkg,'HOSTED_RESOURCE_VALIDATION.json'),resources);
const basis=read(path.join(pkg,'source/basis.json')),inputRoot='C:/Users/Aiden Zhang/Downloads/26025项目方案文件（含P&amp;amp;ID）20261010';
for(const s of basis.sources)if(hash(path.join(inputRoot,s.filename))!==s.raw_sha256)throw Error('CUSTOMER_INPUT_DRIFT');
write(path.join(pkg,'CUSTOMER_INPUT_HASH_RECHECK.json'),{status:'RAW_HASH_MATCH',sources:basis.sources,meaning:'Original DOCX bytes accessible and unchanged; selected quotations in source/basis.json; originals not redistributed'});
const extra=`\n\n## BUILD004：门禁与资源实际验收\n\n镜像采用已核实的精确映射：20261012.333.1/UBR5622或20261021.343.1/UBR5761，OS build20348。实际分配${resources.host.image}/UBR${resources.host.ubr}，${resources.host.logical_processors}核，总${resources.host.total_mb}MiB、启动可用${resources.host.free_mb}MiB。\n\nCPU允许100%分配容量，进程4096MiB/Job8192MiB。480秒上限、kill-on-close、4进程及真实PID核验保留。实际模型耗时${resources.elapsed_model_s.toFixed(3)}秒；PID${resources.actual_python_pid}正常退出，清理后0进程。心跳采样时累计Job内存峰值${resources.sampled_peak_job_memory_MiB.toFixed(3)}MiB（不是完整运行最终峰值，也不是内存压力测试）。不宣称比旧25%配置快了几倍：旧执行没有进入模型，无法公平比较。\n\n11项软件/守恒/失败暴露检查通过；11/11不表示工程PASS。两条轨迹共1200帧，实际表压全部null，受控T2保持HOLD。突然失泵50秒近零流量、亏缺0.949583333m³；没有热模型、真实压力控制或完整00/01接管证明。\n\n旧模型、validation、冻结M1和历史求解器未改；改变的是独立远程执行适配与资源登记。原件00/01再次RAW哈希核对一致。源、环境、官方ZIP/raw摘要、39项原始文件、native源码/二进制及cleanup已独立复核。历史三次失败原包和日志随evidence保留，未在原execution上改源取PASS。\n\n这次完成的是“可运行的预算水力诊断与证据交付”，不是客户完整物理设计验收。下一步优先补真实定压接点/标高/补液膨胀泄压数据与OEM曲线，再开展有依据的单六柜热水力接管；当前不放行18柜或1800秒。\n`;
const md=path.join(pkg,'14_ENGINEERING_REPORT_ZH.md');fs.appendFileSync(md,extra);
const html=path.join(pkg,'15_INTERACTIVE_REPORT.html'),esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
fs.writeFileSync(html,fs.readFileSync(html,'utf8').replace('<section><h2>原始证据入口</h2>',`<section><h2>门禁与资源：实际验收</h2><pre>${esc(extra)}</pre><a href="HOSTED_RESOURCE_VALIDATION.json">资源证据JSON</a> · <a href="retained_failures.json">历史失败索引</a></section><section><h2>原始证据入口</h2>`));
const records=[];function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);if(e.isDirectory())walk(p);else if(e.name!=='16_SOURCE_AND_EVIDENCE_MANIFEST.json')records.push({path:path.relative(pkg,p).replaceAll('\\','/'),bytes:fs.statSync(p).size,sha256:hash(p)});}}walk(pkg);
fs.writeFileSync(path.join(pkg,'16_SOURCE_AND_EVIDENCE_MANIFEST.json'),JSON.stringify({revision:'00-01-HYDRAULIC-V1-BUILD004-REVIEWED',source_commit:review.source_commit,official_zip_sha256:review.official_zip_sha256,source_manifest_sha256:review.source_manifest_sha256,self_excluded:true,records},null,2));
console.log(JSON.stringify({pkg,records:records.length,manifest_sha256:hash(path.join(pkg,'16_SOURCE_AND_EVIDENCE_MANIFEST.json')),resources}));
