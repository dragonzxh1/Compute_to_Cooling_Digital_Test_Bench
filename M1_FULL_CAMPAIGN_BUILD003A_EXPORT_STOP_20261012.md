# Build003a 全量执行：证据导出失效，停止并独立重跑

Run 38261504716，source b9880140d8f927f9469b29d2fe2947fe4e3af93e。
已完成的 prepare/reference jobs 未报告行为 FAIL；但 export.ps1 的 PowerShell 数组拼接优先级
把两个路径合成一个字符串，遗漏 native job / stdout / stderr / admission evidence。
因此整轮标记 INVALID_EVIDENCE_EXPORT，不评价全量 candidate、不继承该轮 PASS。
已请求取消该 run；已上传的 partial artifacts / GitHub logs / source commit 保持历史身份。

Build004 仅修导出路径数组（逐项括号），新增缺少 native evidence 的 fail-closed check。
本地纯文件合成回归验证两个目录确实都导出，无 Python/native/model 执行。
CPU25%、256/512严格内存及1024/2048 campaign、480秒资源预算和所有模型规则不变。
新 execution 必须从 prepare 重新开始；不得把前一轮的 reference 或 Startup collection 拼接。
