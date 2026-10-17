# V2 build1 / run38991246285：保留的审计失败

Execution c88677ab5a175e8519052e0b6817fae5b1571e3f；manifest e52ccd8f72236272c11ec0a0985e58a258ed19873cc5595cc7637b32d681dc9b。

失败场景WET_LOSS_MIXED：独立审计误将“非WARM参数”当成“B罐冷量必定充足”，要求一律完成备用接管，报COMPOUND_TAKEOVER_NOT_COMPLETED。

原始source_phases显示8.9s起B四个观测温度均43.14836°C，高于不变的41.4448°C冷量计量界限；测量冷量为0。控制器正确拒绝，reason=B_COLD_RESERVE_NOT_PROVEN，继续A罐。水量存在不等于冷量已获证明。

Build2只修新增审计的准入条件，并加混合B拒绝回归；不修改协调器、物理模型、阈值、原失败证据或45°C目标。对具备登记冷备用的分层场景仍要求恰好一次接管、实际B选择与原始互锁；对MIXED/WARM明确要求拒绝。整轮从baseline重新fresh，不借本轮PASS。

本轮分层主场景已产生108.7s接管请求、113.7s实际选择B；最高入口46.70191694°C、90秒窗口46.25134881°C，仍超45°C。这些是失败整轮中的局部观察，不认定本轮交付PASS。

本地Git提交后自动gc报损坏对象67b7fe4c2709aeeb8cd7a68519b853a3a5363d9f；未删除/重置/修复主仓库。GitHub CLI Git Data API发布27个精确blob并复核tree/commit一致，保留publication_receipt.json。
