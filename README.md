# AI-PPT 工作台 · v7.2.0

## 7.2.0 工程控制命令

- `python scripts/workbench.py add-input --run runs/运行ID --path 00_inputs/source.pdf --asset-id PDF1`：仅登记已在运行内的文件，PDF显式映射为现有`reference`，不提取内容；不能把`kind`填写为`pdf`。
- `python scripts/workbench.py pipeline --run runs/运行ID`：只校验已有产物并依序推进，缺审批、工具或产物立即`BLOCKED`并返回退出码2；不会自动生成内容、声明能力或审批。
- `block --run … --reason …`、`resume --run …`：保留并复验恢复点，不越过下一审批门；重复阻塞去重。
- `rollback --run … --kind evidence_error --reason …`：仅允许配置内的更早恢复点；快照全部阶段产物，归档并移除全部审批（比仅撤销下游更保守），保留业务文件等待重验。部分失败保留`BLOCKED`。
- `migrate --run runs/旧运行导入副本 --new-run-id 新ID`：旧运行必须先复制到当前工程`runs`；仅复制原始输入和任务，任务回到草稿，能力未知，审批不继承。禁止修改旧锁以假装升级。

渲染校验要求汇报文件为可解析且非空的PPTX，打印文件为可解析且非空的PDF；A3仍执行原页框检测。格式正确不等于视觉或业务QA通过。状态机历史测试使用明确标注的渲染模拟；`tests/test_v63.py`单独执行真实格式负向测试。
工程自动修复与报告节流边界见`config/engineering_control.json`，其本身不提供操作系统权限隔离。

这是交给 TRAE 的项目级工作流对接包，不是一段大提示词，也不是已经部署的后台服务。
适用：接收 PPT、纪要和附件，识别归档、核验、受控优化，分别产出汇报版与打印版。

## 从这里开始
1. 将整个文件夹解压到一个独立项目目录，在 TRAE 中打开。不要先覆盖已有项目规则或 Architect OS。
2. 阅读 `docs/01-闭环审查.md`，然后把 `TRAE_START_HERE.md` 的启动指令发给 TRAE。
3. 确认项目技能 `.trae/skills/` 已被识别；在规则界面导入 `integration/PROJECT_RULES.md` 的短规则。规则入口随 TRAE 版本不同，以实际界面为准。
4. TRAE 先执行能力探测与自检，再接入原始文件。没有实际 PPT 的时候，只能测试框架，不能宣称生成成功。

## 包含什么
- `config/`：工作流、输入输出控制、版式、检索优先站点、上下文预算、Agent 分工、Markdown 样式。
- `schemas/`：可执行 JSON Schema，限制输入与输出的字段和类型。
- `prompts/`：主控与分阶段提示词；每次只加载当前阶段。
- `.trae/skills/`：三项项目技能：工作流编排、优先站点检索、双版式质检。
- `templates/`：Markdown 产物模板与待填入的任务 JSON。
- `scripts/`：初始化、结构校验、门控状态转移、哈希校验与离线测试。它们不生成 PPT、不联网、不替代人工审批。
- `docs/`：逻辑审查、目录与调用路径、审批和数据规则、对接及测试说明、依据与反馈路线。
- `reference/`：原始底稿与 v5，保留溯源；不要作为活动规则加载。
- `examples/`：明确标为演示的结构与门控反例，不含真实业务结论。

## 安装与检查
Python 3.10+；唯一依赖在 `requirements.txt`，离线未安装时需要先安装依赖。
```bash
python -m pip install -r requirements.txt
python scripts/validate_package.py
python -m unittest discover -s tests -v
python scripts/workbench.py init --run-id RUN-001
python scripts/workbench.py validate --run runs/RUN-001
```
`init` 只建立新运行目录，重名会拒绝，不覆盖。填完 `task.json`、`capabilities.json` 再开始业务。

## 真实边界
已封装的是规则、契约、模板和可测试门控；不是已与您本机 TRAE、Architect OS、联网工具或 PPT 渲染器打通的成品应用。
JSON 不会自动变成系统提示词，Agent 名称也不会自动注册成 TRAE 自定义 Agent。由启动指令逐项绑定，并保留能力探测记录。
单 Agent 可以按角色顺序执行；多 Agent 是可选优化，不是运行前提。
包内审批是可审计的人工确认记录协议，不是身份认证系统；有文件写权限的 Agent 能篡改记录，生产级隔离须由宿主权限/受控工具实现。
本包不会建立常驻进程或定时任务。长期运行指长期复用、可恢复、多批次执行；无人值守调度需另行接入持久化执行环境。

## 提示词JSON与规则冻结
`config/prompt_bundle.json` 是已编译的完整提示词JSON，包含正文、源路径、SHA、变量绑定和每次调用的输入输出约定。
Markdown提示词是维护源；修改后运行 `python scripts/compile_prompts.py` 重编译，再执行自检。它不是TRAE官方API请求格式。
运行初始化生成 `config_lock.json`，冻结config/prompt/schema/skill/脚本的哈希；constraints需绑定该锁文件SHA。当前运行不随全局配置静默变化。
web来源在sources中保存snapshot_path，并验证快照SHA。快照不得含未授权保存的机密或超出合理使用的内容。


## v6.1 A3打印版
用户确认打印版为A3。默认横向420×297mm，标题28pt、正文14pt、图表标签与来源12pt；方向/字号除图幅外均为项目默认。
对接验收入口：config/acceptance_plan.json；工具绑定表：config/tool_bindings.template.json；验收记录：templates/acceptance_report.json。
实际PDF图幅检查：scripts/check_print_pdf.py，使用pypdf读取页面尺寸，只做校验不修改PDF。
旧版print_a4不再作为新任务选项，旧运行须留存并按docs/07新建迁移。


## v7对象级门控
工作台规则见WORKBENCH_RULES_V7.md；对象门控见docs/09-对象级排版门控.md。
新增object_layout清单与严格辅助校验。运行004的失败成因已纳入门控；实际源PDF回归结果随本次交付单独保存，不因规则升级默认通过。

## v7.2 纯净对接版
- 已剔除全部业务样本内容与运行证据；仅保留工作台规则、契约、模板、技能与脚本。
- 历史缺陷教训以通用形式保留于docs/08与docs/engineering-bug-lessons.json。
- 真实样本回归验证过的问题均以升级后版本为准；包内不含旧版遗留。
