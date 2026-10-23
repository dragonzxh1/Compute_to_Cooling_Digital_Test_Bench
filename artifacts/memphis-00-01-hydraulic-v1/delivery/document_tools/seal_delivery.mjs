// Hash and package reviewed evidence only. No simulation or native execution.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const pkg='D:/Github/c2c-evidence-review/memphis-00-01-hydraulic-v1/run39912648335/reviewed-delivery';
const mirror='D:/Github/Compute_to_Cooling_Digital_Test_Bench/artifacts/memphis-00-01-hydraulic-v1/reviewed-delivery';
const tools=import.meta.dirname,hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const qa={method:'gstack browse interactive checks on saved remote evidence',
 controlled_59_9:{flow_display:'68.370',permission:false,hold:true},trip_15_0:{flow_display:'≈0.000',permission:false},
 json_edges_rendered:42,mobile_width:390,mobile_scroll_width:390,console_errors:0,
 svg_styles_scoped:true,source_or_raw_model_values_modified:false,
 note:'Display below 1e-6 m3/h is approximate zero only; signed raw residuals unchanged.'};
fs.writeFileSync(path.join(pkg,'REPORT_QA.json'),JSON.stringify(qa,null,2),{flag:'wx'});
for(const file of ['report-desktop.png','report-mobile.png'])fs.copyFileSync(path.join(path.dirname(mirror),file),path.join(pkg,file));
const docTools=path.join(pkg,'document_tools');fs.mkdirSync(docTools);
for(const f of ['assemble.mjs','diagram.mjs','finalize.mjs','finish_display.mjs','scope_svg_style.mjs','review_build002.ps1','seal_delivery.mjs'])fs.copyFileSync(path.join(tools,f),path.join(docTools,f));
const readme=`# 00/01 水力预算与定压 V1 — BUILD004\n\n先打开15_INTERACTIVE_REPORT.html；查看14号中文报告及HOSTED_RESOURCE_VALIDATION.json。图纸12号SVG/PNG按02号JSON生成，是约简研究功能图，不是施工P&ID。\n\n源码/执行commit：274871a94ef13680c508a736ea9635095570cecb。\n官方run：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39912648335\n\n仅GitHub远程短程研究。没有本机模型/native运行、18柜、1800秒、正式C3-C、真实设备、采购或工程批准。冻结M1和历史求解器未改。\n\nCPU rate10000允许使用runner全部分配容量，不再25%节流；进程4096MiB/Job8192MiB，480秒终止与清理保留。实际模型耗时1.421秒；不得据此推断未来长程模型耗时。\n\n11个软件检查PASS；物理结论仍分开：定压OPEN，T2受控交接INCOMPLETE/HOLD，突然失泵FAIL。下一步需先补真实压力边界与OEM数据。\n\nCSV：01压力预算，05研究QH包络，06条件性HX跨侧差压，07各支路损失，09未闭合吸入口/NPSH/承压，10/11两场景。两份NDJSON保留全部1200帧的节点/边、求解诊断及原始有符号数值。evidence保留完整远程baseline、native来源和二进制、环境、原始日志及三次失败官方包。\n\n16号清单列出所有文件字节数和SHA256，自身排除。external ZIP摘要记录在独立发布收据，避免自引用。document_tools仅用于重建文档/核验保存证据，里面的绝对路径需要按下载位置调整；不能当作本机模型启动入口。\n`;
fs.writeFileSync(path.join(pkg,'README_ZH.md'),readme,{flag:'wx'});
const mf=path.join(pkg,'16_SOURCE_AND_EVIDENCE_MANIFEST.json'),m=JSON.parse(fs.readFileSync(mf));
const rows=[];function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);if(e.isDirectory())walk(p);else if(p!==mf)rows.push({path:path.relative(pkg,p).replaceAll('\\','/'),bytes:fs.statSync(p).size,sha256:hash(p)});}}walk(pkg);
m.records=rows;fs.writeFileSync(mf,JSON.stringify(m,null,2));
for(const r of m.records){const p=path.join(pkg,r.path);if(hash(p)!==r.sha256||fs.statSync(p).size!==r.bytes)throw Error('PACKAGE_HASH');}
fs.cpSync(pkg,mirror,{recursive:true});
console.log(JSON.stringify({manifest_sha256:hash(mf),records:rows.length,pkg,mirror}));
