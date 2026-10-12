# 本地 Git 对象损坏观察：与远端 campaign 分开

发布 Build005 plan 进度文档时，git commit 自动触发 gc/repack，报 `incorrect data check`
及 loose object 损坏。文档提交 `cd94aeb624535a0b46b0059db0011bb39186e953` 和 GitHub CLI
认证推送仍成功；已通过 GitHub API 确认远端提交及两个文档文件存在。

损坏对象：`843de9ee7f8a580883f0776dd6e183b02f08fbeb`。
位置：`D:/Github/Compute_to_Cooling_Digital_Test_Bench/.git/objects/84/3de9ee7f8a580883f0776dd6e183b02f08fbeb`。
压缩文件 492,853 bytes；header 可读取为 blob / 7,700,713 bytes，但不代表完整 body 可解压。
压缩文件 RAW SHA-256：`f9642efb66c18635e01452d36033585549a242ad4dd0276f10fceefe5b6683a2`。
原文件时间记录：2026-10-12T16:11:17.6557841Z。
GitHub blob API 对这个对象返回 404；其来源和是否属于本地 snapshot 尚未确定。

仅将原损坏 bytes 复制至
`D:/Github/Compute_to_Cooling_Digital_Test_Bench/artifacts/git-object-corruption-20261013/843de9ee7f8a580883f0776dd6e183b02f08fbeb.corrupt.zlib`
并核验 RAW hash 一致。未删除、替换或重写原对象，未 reset/checkout 用户数据，
未手动运行全仓 fsck/gc/repack，也未运行本地 Python/native/model 测试。
后续发布提交只用单次命令 `git -c gc.auto=0 commit ...` 避免再次自动整理；不改全局配置。
在没有可靠对象来源时不猜测恢复内容；对象恢复作为独立待处理问题保留。

远端 run38269665488 始终绑定原冻结 source9b487ce，不受后续文档提交影响。
该观察不是 candidate FAIL，也不能证明此前整机硬挂的根因。
报告时远端 plan 已 PASS，prefix/Startup 正在继续；全量 campaign 尚未完成。
