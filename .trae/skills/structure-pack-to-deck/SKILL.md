---
name: structure-pack-to-deck
description: 将PPT结构包(layout-protocol v1.1 zip, 含结构定义JSON与素材)转换为ppt-engine deck并渲染出PDF。当用户发来结构包zip并要求"跑一下/重新整理/调整章节页码/删页移页"时使用。含新项目隔离、类型映射、4列表压缩、章节色接入、占位图识别与逐页缩略图验收流程。
---

# 结构包 → ppt-engine deck 渲染流程

处理「PPT 结构包」(layout-protocol v1.1)：对方发来 zip，内含结构定义 JSON（逐页内容内嵌）与素材文件夹，目标是产出 26~29 页规格的 PDF 成品。完整模板数据契约见 [references/template-contracts.md](references/template-contracts.md)，转换器参考实现见 [scripts/build_deck_template.py](scripts/build_deck_template.py)。

## 输出锚定（必读，2026-10-16 用户拍板）

- **正式交付物一律以 PDF 为准**（ppt-engine 渲染），便于体现高端商务感；PPT 结构定义 JSON 是唯一上游接口，PDF 是唯一正式成品锚点。
- **python-pptx 渲染的 PPTX 仅限草稿自查**（快速核对内容/数据/页序），**禁止作为正式稿交付**——它做不出遮罩、分章色、精排版，封面/分隔页尤其劣化。
- 封面（cover）、章节分隔（divider-a/b/c）、结尾（closing）等大版面页**必须走 ppt-engine 模板**：cover 用 bg_image 全幅+底部 footer 自适应变色；divider 按内容选变体（有图选 a、纯排版选 b、需本章摘要选 c 必填 4 条 points）；closing 支持 bg_image + concept_recap。
- 收到结构 JSON 后，默认直接进入本 skill 的 ppt-engine 流程，不要先用 python-pptx 出片再返工。

## 版式与文案基线（引擎层规则，2026-10-16 用户拍板，全项目复用）

**1. 字号基线（正文/明细整体放大一号）**
- 权威源：`ppt-engine/base.css` + `ppt-engine/templates/*.html`（模板内是硬编码 px，**外挂 theme.json 的 `--fs-*` 管不到**，改字号必须改这两处）。
- 现行基线：`.card-text` 17px、`.data-label` 17px、`.data-item` 14px、`.feature-list li` 15px、`.compare-item` 15px、对比表表体 15px、`.sum-item` 14px、案例图题注 15px、full-text `.ft-text` 19px、multi-card 页脚大字 19px。
- 改完必须**双份同步**（`ppt-engine/` → 根目录 `base.css`、`templates/`），再重建 `ppt-engine.zip`（排除 workdir/slides/build/缓存），最后**必看缩略图确认字号真的生效且密集页无截字**。

**2. 页数标注一律不出现**
- 页脚页码：`base.css` 末尾 `.page-number { display: none; }` 统一停用（各内容模板仍保留 div，但不渲染）。
- 目录页码：deck 的 toc 数据**不传 `pages`**；`toc.html` 已加 `.toc-pages:empty { display: none; }` 兜底，空则不占位。

**3. 文案禁元话语（标题/引言/大字/脚注都必须扣题）**
- 禁止「不喊口号」「概念不止于词」「三个词各落一组动作」这类自我说明式表述——它们是口水话，不承载信息。
- 每处显眼文案都要**直接呈现实质内容**（做法、数据、结论），且**只能从既有论据取材**（如本项目 87.5m 模数单元、U 北一字南、3F→4F 弹性加建），不得为凑句发明新数据。
- 结构定义 JSON 的修改**另存新版本号**（如 v2→v3），原版本保留，`version_notes` 记录用户拍板内容。

**4. 封面底图取向**
- 用**浅灰暖调、清晨薄雾、低对比度的近景实景**（现代厂房立面/幕墙），与封面白雾蒙层天然兼容；**不用鸟瞰大场景**（易显廉价、与蒙层打架）。
- 旧图存档为 `bg/cover_v1.jpg`，新图覆盖 `bg/cover.jpg`，workdir 与项目盘 assets **双份同步**（生成图右下角常带「AI生成」水印，裁掉底部 10% 即可清除）。

**5. 配图必须按容器比例出图（否则被 object-fit: cover 裁掉）**
- `split-image-text` 的图片容器实测 **766 × 555 pt ≈ 1.38 : 1**（`image_second` 存在时上方主图仍为该比例）；`.split-left img` / `.split-main img` 走 `object-fit: cover`，**超宽图会被横向裁切**——2.68:1 的横向三栏示意只露出约 51%（中间栏），两侧内容全丢。
- 出图前先按 1.38:1 排布：宽幅内容改为「上两栏 + 下通栏」，或整体压成近方形；已有素材（site/vision 等）沿用时可不动。
- **验收一定看缩略图**：图被 cover 裁切不是渲染报错，只看文件名/日志发现不了（本项目 v3 的 vision 图就漏了一次，v4 才发现）。

## 流程

1. **新项目隔离**：在 `ppt-engine/workdir/<项目名>/` 建独立目录，绝不污染其他项目根目录。骨架：`source/`(结构包归档)、`slides/`、`build/`、`build/_diag/`、`assets/`、`deck.yaml`、`build_deck.py`。
2. **解包落位**：结构 JSON 存 `source/结构定义_vX.X.json`；素材文件夹(如 `deyang_assets/`)内容合并进 `assets/`（协议路径 `bg/cover.jpg` 对应 `assets/bg/cover.jpg`）。
3. **写一次性转换器** build_deck.py（复制模板改映射），产出 deck.yaml。核心映射规则：
   - 类型映射：`image-text-split`→`split-image-text`；`three-cards`/`data-profile`→`multi-card-row`；`comparison-table`→`compare-table`；`chapter-divider`→按页分配 a/b/c 变体
   - `asset_path()`：协议路径 → slides 视角 `../assets/...`
   - `slide.chapter`(ch1..chN) 由 JSON `chapters[].pages` 页码范围推导，接入分章色（theme.json `chapter_colors`）
   - divider-c 变体必填 `points: [{num,title,desc}]`（从本章内容提炼 4 条）
   - 4 列表压缩进模板固定 3 列：对比语义(指标/原规划/调规后/变化)→热列+备注 `原值（变化）`；通用语义→第3/4列 `<br>` 合并进备注列
4. **渲染出 PDF**：
   ```
   python ppt-engine/main.py render --project <项目目录>
   python ppt-engine/main.py pdf --project <项目目录> --out <项目目录>\build\<名称>.pdf
   ```
5. **缩略图验收**：pymupdf 按 `Matrix(0.42,0.42)` 导出 `build/_diag/pNN.png`，逐页 Read 检查（重点：长标题、表格列、分隔页变体、分章色、图片页）。

## 已知坑（必读）

- **数据源纯净**：内容全部内嵌 JSON 时不要做 MD 兜底——divider/cover 页无 content 键，会被旧 MD 覆盖导致模板分布错乱。转换器只用 JSON。
- **素材占位图**：包内 `site/` 等目录的小体积 PNG(10~40KB) 常是对方自带的"待替换"示意图（米灰底对角线+英文标签），如实渲染，不要当 bug 修。缺失图片渲染器自动置空出占位相框，无需处理。
- **页数增删后**：删除 `slides/` 中多余旧 HTML 再渲染；重排页码时 divider 页自带的 `chapter_num` 字段要同步顺移。
- **模板修复双份同步**：`ppt-engine/templates/*.html` 与根目录 `templates/*.html` 两份都要改，改完重建 `ppt-engine.zip`（排除 workdir）。
- **版本管理**：改版前把旧 PDF 复制为 `build/<名称>_vX.X存档.pdf`；调整版结构 JSON 另存新版本号，原包不动。
