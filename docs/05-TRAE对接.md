# TRAE 对接与实施边界

## 已核实的官方能力
TRAE官方技能文档说明项目级技能在 `.trae/skills/{name}/SKILL.md`，并采用按需加载。
来源：https://docs.trae.ai/ide/skills （2026-10-23读取）
官方博客介绍项目规则、独立Agent提示词和项目相对路径。它不是对所有新旧版本UI一致性的承诺。
来源：https://www.trae.ai/blog/trae_tutorial_0825 （2026-10-23读取）
本次 `https://docs.trae.ai/ide/rules` 正文读取超时，未以该页作为规则安装格式依据。

## 安全接入顺序
1. 单独打开本项目。项目规则通过UI导入 integration/PROJECT_RULES.md；不猜测未经验证的自动规则文件名。
2. 检查三项项目技能被识别；否则手动调用，不把整个包一次塞进上下文。
3. 执行包内自检，再执行能力探测，登记实际工具名称/版本/观察到的证据。没有工具就标missing。
4. 若使用自定义Agent，按 config/agents.json逐项创建并绑定对应prompt；没有多Agent功能则单Agent切换角色。
5. 将已有Architect OS纪要作为文件输入，不重新实现它，也不直接读其全部历史会话；内容与数字独立核验。
6. 实现渲染器适配：输入deck、profiles、源资产；输出artifacts.json与真实文件。适配器必须支持保留源PPT与另存副本，无法做到时只能输出修改提案。
7. 实现人工审批桥接：人工UI决定 → 凭据文件 → approval JSON。不能让执行Agent拥有“自批”的默认权限。
8. 在本地跑首份真实PPT：识别覆盖 → 约束 → 方案 → 页框架 → 双版渲染 → QA → 批准交付。

## 本包脚本负责与不负责
负责：结构校验、路径防逃逸、原件哈希、状态边、审批哈希、上下游版本绑定、待核关键事实拦截、实际文件清单校验。
不负责：读PPT/扫描/OCR/真实计算公式解释、联网、生成PPT、实际字体与视觉验收、真实人身份认证、操作系统级权限隔离、后台调度。
这些都由TRAE/本地工具提供，且记录真实可用性。未验证不能写成已上线。

## 常用命令
```bash
python scripts/workbench.py init --run-id RUN-001
python scripts/workbench.py validate --run runs/RUN-001
python scripts/workbench.py check-transition --run runs/RUN-001 --to IDENTIFIED
python scripts/workbench.py transition --run runs/RUN-001 --to IDENTIFIED
python scripts/workbench.py status --run runs/RUN-001
```
每次仅转移一条合法边。脚本无“自动批准”命令；外部写入人工批准记录以后再检查门控。
脚本拒绝跳阶段、旧哈希审批、待核关键事实和未检查的QA。人工绕过脚本或篡改审计并不能被本包完全阻止。

## 后续反馈
用 templates/feedback.md 和 feedback.json。提交包版本、运行ID、出错状态、最小复现、期望与实际、脱敏文件路径、QA截图。
不要回传凭据/个人信息/整个客户资料。规则修改以新版本包发布，保留旧版便于回滚。

## Prompt JSON 适配
从config/prompt_bundle.json按当前角色取content；变量值由task和状态绑定，缺失业务必填项先阻塞。
它是本项目应用层契约，不假设TRAE接受某个官方JSON导入接口。手动Agent提示词可使用同源Markdown正文。
每次调用结果按schemas/envelope.schema.json；业务文件仍按各自Schema验证。
