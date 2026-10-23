---
name: ppt-workbench
description: 在本项目收到PPT或纪要、继续一轮优化、恢复运行或交付双版成品时，按状态与门控编排工作流。
---

# ppt-workbench


1. 根目录读integration/PROJECT_RULES.md、当前runs/{run_id}/state.json和短索引。
2. 按config/workflow.json和config/agents.json加载唯一当前阶段prompt，不加载全部历史。
3. 识别与标签、约束草案自动；确认事件按哈希审批；保护变更单独授权。
4. 每步输出按schemas校验，以scripts/workbench.py推进。失败保持现场，禁止越级。
5. 二级记忆只按需读取，交接使用envelope；上下文拥挤时输出handoff恢复包。
6. 发布前核验真实文件、QA与审批，反馈只生成提案。

## renderer 阶段（ppt-engine 接入）

工作台自身是状态门控与编排骨架，**不直接渲染**——渲染引擎为 `ppt-engine/`（28 个 HTML 模板 + 5 个主题 + 13 个渲染脚本）。renderer 阶段具体调用：

```bash
# 已有 deck.yaml 的项目重渲
python ppt-engine/main.py rebuild --project <项目目录>

# 只渲指定页
python ppt-engine/main.py re-render --project <项目目录> --slides 20,22,25

# 协议 v1.1 结构包（ZIP）→ deck.yaml → PDF
# 先用 structure-pack-to-deck 技能把结构包转成 deck.yaml，再 rebuild
```

deck.yaml 每页契约：`{id, chapter, template, title, status, data, page_num}`。template 名直接对应 `ppt-engine/templates/*.html`（cover-soft、toc、chapter-divider-a 等 28 种）。主题选 `ppt-engine/theme.json` 或 `themes/<五选一>.json`。

系统 Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`）已验证可用；build_pdf.py 内置 `channel="chrome"` fallback，无需预装 playwright chromium。
