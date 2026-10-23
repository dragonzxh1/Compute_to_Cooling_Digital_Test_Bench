# BUILD002：远程环境及资源登记更新

用户于本聊天授权同时解决环境门禁并调整远程资源。

- BUILD001 commit `7204410221fb161ae70858e8d20b5234098a4b67`、run `39909757507` 保持失败：`IMAGE_DRIFT`，模型未开始，不是水力计算失败。
- 失败官方ZIP SHA256：`88ca350286147139d65bca6899580876dd553770715e1a04229908034466b82a`。
- 失败日志ZIP SHA256：`62f2d552fc2d16a382e317591921a97ee21d50edcde71716c02289e861535e22`。
- 本版本只更新环境、资源和执行适配；network.py、validation.py、00/01原始依据、阈值和历史求解器均保持原字节。

## 新登记

GitHub公共 windows-2022；镜像20261021.343.1、OS build20348/UBR5761；Python3.11.9、NumPy2.4.6。
官方镜像更新：https://github.com/actions/runner-images/releases/tag/win22/20261021.343

允许使用分配runner的100% CPU容量（Job CPU rate10000，不再25%节流）。进程4GiB/Job8GiB；启动前要求主机总内存≥12GiB、可用≥10GiB，保留系统余量。480秒模型上限、4进程上限、kill-on-close、真实Python PID入Job证明、清理验证均保留。BLAS单线程用于保持数值执行顺序，不是25% CPU限制。

原m1_remote_executor_v1源码未修改。此命名空间内的执行器副本只改变资源参数准入，VerifyTarget验证器保持原字节；在远端编译与运行ABI检查和旧策略拒绝检查。本机不运行Python/模型/native测试。

仅运行登记的单六柜短程水力研究；无18柜/1800秒、正式C3-C、采购、生产、真实硬件或Phase6授权。实际定压资料缺失仍保持OPEN，不能将软件执行PASS写成工程PASS。
