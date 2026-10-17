# 单柜优先 Build1失败保留

执行源码4093b7d9e4fc5cf2761c2c517b6c6644ab6618ca，run39009958272，source manifest9981f8e7a32d02d7631b6b23aadab21a364a221319f22905750734095f32330b。

旧基线fresh回归通过。COMPONENT阶段FAIL，错误`COMPONENT_REFINEMENT_FAIL`；后续NEGATIVE/单柜/六柜/报告未执行，不借此标PASS。官方原始ZIP、执行结果、日志和实际Job证据保存在`D:/Github/c2c-evidence-review/memphis-single-rack-v1/failed-run39009958272/`。

根因：新部件校核中rate单位W，代码`t+=dt*rate`漏除capacity（J/K），不是正确的温度更新。较大错误状态可变为非有限值，使原绝对残差比较不能提供有效证据，最后步长收敛检查拒绝。没有修改旧仿真或冻结数学核心。

Build2只修新COMPONENT校核的能量/热容量换算，增加非有限值立即停止。动态RackLoop中原有`dt*rate/capacity`公式保持不变；45°C、满载、M1、来源保护和原检查门槛不放宽。以新source snapshot和commit重新从baseline全轮fresh执行，不重跑旧failed jobs，不把旧FAIL改为PASS。
