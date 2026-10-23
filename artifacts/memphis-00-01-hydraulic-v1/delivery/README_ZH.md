# 00/01 水力预算与定压 V1 — BUILD004

先打开15_INTERACTIVE_REPORT.html；查看14号中文报告及HOSTED_RESOURCE_VALIDATION.json。图纸12号SVG/PNG按02号JSON生成，是约简研究功能图，不是施工P&ID。

源码/执行commit：274871a94ef13680c508a736ea9635095570cecb。
官方run：https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39912648335

仅GitHub远程短程研究。没有本机模型/native运行、18柜、1800秒、正式C3-C、真实设备、采购或工程批准。冻结M1和历史求解器未改。

CPU rate10000允许使用runner全部分配容量，不再25%节流；进程4096MiB/Job8192MiB，480秒终止与清理保留。实际模型耗时1.421秒；不得据此推断未来长程模型耗时。

11个软件检查PASS；物理结论仍分开：定压OPEN，T2受控交接INCOMPLETE/HOLD，突然失泵FAIL。下一步需先补真实压力边界与OEM数据。

CSV：01压力预算，05研究QH包络，06条件性HX跨侧差压，07各支路损失，09未闭合吸入口/NPSH/承压，10/11两场景。两份NDJSON保留全部1200帧的节点/边、求解诊断及原始有符号数值。evidence保留完整远程baseline、native来源和二进制、环境、原始日志及三次失败官方包。

16号清单列出所有文件字节数和SHA256，自身排除。external ZIP摘要记录在独立发布收据，避免自引用。document_tools仅用于重建文档/核验保存证据，里面的绝对路径需要按下载位置调整；不能当作本机模型启动入口。
