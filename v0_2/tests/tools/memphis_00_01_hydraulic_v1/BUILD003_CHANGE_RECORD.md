# BUILD003：明确覆盖滚动部署中的两个已核实镜像

BUILD002 run39911963438、commit0aec52a4a836ff42e44e03ce8507945c727742cf被预检拒绝：登记20261021.343.1，实际分配20261012.333.1/UBR5622。模型与native均未启动。官方ZIP及日志已下载保存；失败不覆盖。

实际主机4核，总16378MiB，可用13953MiB；满足4GiB进程/8GiB Job及系统余量。BUILD003资源策略不变，仅将镜像准入改为精确映射：

- 20261012.333.1 → Windows build20348/UBR5622。
- 20261021.343.1 → Windows build20348/UBR5761。

两个官方发布说明均独立核实；不是接受未知未来镜像。Python/NumPy/动作版本、模型、求解器和期待不变。

官方来源：https://github.com/actions/runner-images/releases/tag/win22/20261012.333 及 https://github.com/actions/runner-images/releases/tag/win22/20261021.343 。
