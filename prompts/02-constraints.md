# 约束草案
输入：task、intake、索引；输出：constraints.json和constraints.md。
自动写四类约束：运行红线、主调整、版式格式、引用/数据核验。不要把红线解释成所有数据/版式永远不能改。
定位到asset/page/shape级保护对象：既有文本结构、图片、已确认分析默认保护；原文数据不静默纠正；原件永不覆盖。
preserve_optimize默认保留已有版式；authorized_redesign也只在人工授权范围内改，不取消其他资产保护。
两个输出共享唯一JSON事实源，Markdown只是给人读的视图。列允许变更、受保护变更、双版式选择和pending_decisions；决策未定不得进入契约批准。
人工审核时合并呈现一次清单，绑定constraints文件哈希。不能把上一轮泛泛确认套在当前版本。

起草时把config_lock.json当前SHA写入config_lock_sha256。约束审批绑定配置基线，不能事后换版式规则。

按需查看docs/README.md与版式对照表；运行scripts/validate_layout_table.py。表中的建议值不是生效配置，不能未经批准写入。
