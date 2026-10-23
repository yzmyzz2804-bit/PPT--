# 发给 TRAE 的首次启动指令

请在当前项目接入 AI-PPT 工作台 v6，不要改动现有 Architect OS 或覆盖已有规则。

1. 先读 `README.md`、`integration/PROJECT_RULES.md`、`config/workflow.json`、`config/agents.json` 与 `docs/05-TRAE对接.md`。不要递归读取整个项目。
2. 运行 `python scripts/validate_package.py` 与 `python -m unittest discover -s tests -v`，返回真实检查结果。
3. 检查 `.trae/skills/` 三项技能是否加载；不支持自动发现则报告，并以显式读取 SKILL.md 作为降级。不要声称已安装。
4. 逐项探测本地文件读取、PPT 文本/备注/图表/图片提取、OCR、联网搜索、正文读取、PPT 编辑、双格式渲染、视觉检查、字体可用性和人工审批入口。结果记录到新运行目录的 `capabilities.json`，不要猜测工具名称。未具备的关键能力进入 BLOCKED；不以提示词代替工具。
5. 使用 `python scripts/workbench.py init --run-id RUN-001` 创建新任务；如已存在则读取其状态或换新 ID，不覆盖。
6. 将用户提供的文件复制到该运行的 `00_inputs/`，登记相对路径和 SHA-256。原件只读；Architect OS 只交接纪要内容，没有数据核验权。
7. 自动完成识别、标签与约束草案。在运行契约/保护范围确需人工决定时才停下；不得对每个小动作重复确认。识别不清记录为 unknown，不能假装人已确认。
8. 首次运行先向用户汇总：输入是否可读、任务模式、保护资产、版式配置、缺失能力、审批点。项目级默认值可以采用，业务字段和行业站点不得编造。
9. 按 `prompts/00-controller.md` 编排，只按当前状态加载对应提示词。每次状态转移先执行 `check-transition`，再执行 `transition`；工具检查失败不得靠修改 state.json 跳过。
10. 最终返回交付清单、版本/哈希、真实质检结论、尚未通过的项、下一次可恢复状态；反馈写入模板，规则升级先出提案再请人工批准。

先做对接和能力报告，不要在没有原始 PPT 的情况下生成业务成品。


## 当前活动版本7.2.0

工程控制与PDF登记命令见README。遇到缺审批时使用pipeline安全阻塞，不得为跑通补造审批。旧冻结运行迁移到新运行，不原地重锁；工程修复边界见config/engineering_control.json。

## 历史v6.1 A3补充执行
打印版用户已确认A3。先读取config/acceptance_plan.json、config/tool_bindings.template.json和templates/acceptance_report.json，执行其中可执行项；不可执行项记录blocked/not_checked。
默认A3横向420×297mm；方向待定不要反复打断，先纳入契约汇总。不能承袭旧print_a4任务标识。
渲染后执行python scripts/check_print_pdf.py --file <真实打印版.pdf> --orientation landscape --output <当前运行>/05_qa/a3-size-check.json。
旧v6任务不要原地覆盖：旧审批绑定旧配置，应保留旧目录，使用新run_id迁移并重新确认受影响内容。

## v6.2 版式表接入要求
先读docs/README.md文档索引，再按需读取docs/双版式版式规范对照表_A3与汇报版.xlsx。
约束/策划角色使用表中的状态区分已配置与建议；渲染/QA以config/layout_profiles.json为执行依据。
首次接入及每次改版式后运行python scripts/validate_layout_table.py；总自检也会自动执行该检查。
字段映射见config/layout_table_mapping.json；任一不一致先阻塞相关版式操作，人工确认后同步配置、表格和映射，重编译提示词并回归。
不要为让检查通过自动重建映射基线，不能把建议值自动写入已批准配置。


## 对象级排版强制入口
先读取WORKBENCH_RULES_V7.md和docs/09-对象级排版门控.md。
不复用004的几何切块方法。渲染器先生成03_content/object_layout.json，再用scripts/check_object_layout.py验证；失败不可进生产渲染通过状态。
对象未完整重建只能标参考或未完成；实际逐页QA不得用字体尺寸或字符覆盖代替表格/图纸语义完整。

## v7.1最终验收入口
先读docs/12-最终验收清单.md与docs/run006-machine-checks.json。真实样本回归以006修复件为准：机制检查全通过、视觉有限审阅、未承诺逐字视觉通过；遗留8项不硬凑。生产渲染仍按L01—L09对象门控。

## 正常使用流程（TRAE端）
1. 解压本包到独立项目目录，在TRAE中打开；不覆盖已有项目规则与Architect OS。
2. 阅读README.md与docs/README.md文档索引，再把integration/PROJECT_RULES.md设为项目级短规则（规则入口以实际界面为准）。
3. 确认.trae/skills/三项技能（ppt-workbench、preferred-source-research、dual-layout-qa）被识别；不支持自动发现则显式读取SKILL.md作为降级，不声称已安装。
4. 运行python scripts/validate_package.py与python -m unittest discover -s tests -v，返回真实结果。
5. 逐项探测本地能力并登记capabilities.json：file_read、ppt_extract、ocr、web_search、web_read、ppt_edit、pdf_render、visual_inspection、fonts、human_approval；未实测填unknown，不以提示词代替工具。
6. python scripts/workbench.py init --run-id RUN-001创建运行；重名拒绝覆盖。用户提供的文件放入00_inputs/并用add-input登记哈希。
7. 自动完成识别、标签、约束草案；受保护改动与业务决策按门控停下，不逐小动作打断。
8. 按config/object_layout_gates.json的L01—L09执行对象级渲染：正文段落流动、表格按行列分页并重复表头/主键、图纸完整不切割；生成03_content/object_layout.json并用scripts/check_object_layout.py校验，失败不得进入通过状态。
9. 汇报版16:9与打印版A3横向420×297mm分别渲染；字号、边距等以config/layout_profiles.json为准，版式表docs/双版式版式规范对照表_A3与汇报版.xlsx为人读对照。
10. QA按六类检查（结构/数字/视觉/跨版/审批/交付）；未通过或未检查不得发布。发布经审批后复制到06_release并核哈希。
11. 反馈写入templates/feedback模板：提案→人工批准→新版本→回归；不自动修改工作流。

## 纯净包说明
本包不含任何业务样本内容或历史运行证据；首次接入需用你自己的实际文件走完整流程。
