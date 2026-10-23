# PPT 概念方案生成引擎 · COZE Agent 调用说明

## 这是什么

一套可独立运行的 Python 工具链，从参考 PDF + Excel 指标表 + 效果图，自动生成 54 页左右的建筑规划概念方案 PPT（PDF 输出）。

## 依赖 & 预装

```bash
# 1. Python 3.10+ (推荐 3.13)
python --version

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器 (必须,否则无法渲染 PDF)
playwright install chromium
```

> **COZE 沙箱注意事项**：
> - Playwright 的 `channel="chrome"` 会尝试用系统 Chrome，沙箱里大概率没有。
> - 但 `build_pdf.py` 已经做了 fallback：先尝试 Chrome，失败自动回退到 Playwright 自带的 Chromium。
> - 所以只要 `playwright install chromium` 跑过一次就行。

## 目录结构（解压后）

```
ppt-engine/
├── main.py                 # ★ 唯一入口,COZE agent 只调这个
├── coze_runner.py          # ★ 一键 runner(自动解压+装依赖+调 main.py,输出 JSON)
├── requirements.txt        # pip install -r 用
├── base.css                # 基础样式 (勿改)
├── theme.json              # 配色/字体/尺寸 (勿改)
├── templates/              # 17 个版式 HTML (勿改)
└── scripts/                # 子脚本 (勿直接调,main.py 封装)
    ├── _env.py
    ├── parse_v2_pdf.py     # 从参考 PDF 抽页面结构
    ├── fill_from_ref_pdf.py # 从参考 PDF 抽每页文字+分析图回填(成果版关键)
    ├── parse_excel.py      # 从 Excel 抽指标数据
    ├── parse_coze_md.py    # 从 COZE MD 草稿抽概念主旨
    ├── fill_content.py     # 按章节均分内容点
    ├── build_book.py       # book 模式: 图片+文字 → PDF
    ├── render_protocol.py  # protocol 模式: page_protocol.json → deck.yaml → PDF
    ├── render_slide.py     # 模板 → HTML
    ├── build_pdf.py        # HTML → PDF
    ├── build_pptx.py       # (可选) HTML → PPTX
    └── gen_bg.py           # (可选) 文本分析→智能生成封面+每章意向图(沙箱无API需skip)
```

## COZE Agent 调用流程（4 步）

### 第 1 步：收集素材

把用户给的所有素材放到临时目录，比如 `/tmp/coze_project/`：

```
/tmp/coze_project/
├── ref.pdf              # 用户给的参考版 PDF (必须)
├── 指标表.xlsx            # Excel 指标表 (推荐)
├── 效果图/                # 效果图文件夹 (推荐)
│   ├── 鸟瞰1.png
│   ├── 鸟瞰2.png
│   ├── 透视1.png
│   └── 透视2.png
└── 项目名.md              # COZE 输出的 MD 草稿 (可选)
```

### 第 2 步：解压引擎 + 安装

```bash
cd /tmp/
unzip ppt-engine.zip -d ppt-engine
cd ppt-engine
pip install -r requirements.txt
playwright install chromium
```

### 第 3 步：一条命令出 PDF

```bash
python main.py build \
    --name "安岳县柠檬冷链共享仓建设项目" \
    --ref-pdf /tmp/coze_project/ref.pdf \
    --excel /tmp/coze_project/指标表.xlsx \
    --renders /tmp/coze_project/效果图 \
    --skip-bg-gen
```

参数说明：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--name` | ✅ | 项目名称，用于 PDF 标题和输出目录名 |
| `--ref-pdf` | ✅ | 参考 PDF 路径（引擎从这里抽页面结构） |
| `--excel` | | Excel 指标表路径 |
| `--renders` | | 效果图目录 |
| `--md` | | COZE 输出的 MD 草稿路径 |
| `--project-type` | | `industrial_park`（默认，不触发口号页）/ `real_estate`（触发口号页）/ `other` |
| `--skip-bg-gen` | ⭐ | **COZE 沙箱必须加**，因为没有 trae-api 图像生成服务 |
| `--project` | | 自定义输出目录（默认 `workdir/<项目名>/`） |
| `--output` | | 自定义 PDF 输出路径 |

### 第 4 步：取回 PDF

PDF 在 `workdir/<项目名>/build/<项目名>.pdf`（或 `--output` 指定路径）。

同时生成的文件：
```
workdir/<项目名>/
├── deck.yaml              # ★ 可编辑! 修改后 re-render 即可迭代
├── slides/slide_*.html    # 每页的 HTML
├── build/
│   ├── deck.html          # 组合后的单 HTML (调试用)
│   └── <项目名>.pdf       # ★ 最终 PDF
└── assets/images/renders/ # 自动复制的效果图
```

## 两种生成模式

### 模式一：build（完整 PPT 流程，默认）

参考 PDF + Excel + 效果图 → 54 页左右完整方案 PPT。流程见上面 4 步。

用 coze_runner.py 一键跑（自动解压+装依赖+构建，输出 JSON）：

```bash
python coze_runner.py \
    --name "安岳县柠檬冷链共享仓建设项目" \
    --ref-pdf /tmp/coze_uploads/ref.pdf \
    --excel /tmp/coze_uploads/指标表.xlsx \
    --renders /tmp/coze_uploads/效果图 \
    --zip-path /tmp/coze_uploads/ppt-engine.zip
# 成功: {"success": true, "pdf_path": "...", "size_kb": ...}
# 失败: {"success": false, "error": "..."}
```

### 模式二：book（图片+文字直接封装 PDF）

不要完整 PPT，只要把效果图/文字排成成果版 PDF：

```bash
# 目录模式(丢图片自动按文件名排序)
python coze_runner.py --mode book \
    --name "项目名" \
    --images /tmp/coze_uploads/效果图

# YAML 模式(每页可写标题/副标题/说明)
python coze_runner.py --mode book \
    --name "项目名" \
    --config /tmp/coze_uploads/pages.yaml \
    --layout 16:9 --theme warm
```

pages.yaml 格式：

```yaml
project: 项目名
layout: 16:9        # 16:9 / A4
theme: warm         # warm 暖纸白 / dark 深色 / plain 纯白
pages:
  - image: 鸟瞰1.png
    title: 鸟瞰效果图
    subtitle: 方案总览
    caption: 从东南方向俯瞰整个冷链园区
```

## 迭代模式（已有项目）

用户看了 PDF 说"第 25 页指标数据要改"——不用重跑全流程：

```bash
# 编辑 deck.yaml (直接改 p25 的 data.rows)
vim workdir/<项目名>/deck.yaml

# 只重渲染改动页
python main.py re-render --project workdir/<项目名> --slides 25

# 或全量重建
python main.py rebuild --project workdir/<项目名>
```

## 模式三：protocol（PPT Layout Protocol v1.0）

COZE 概念层直接输出 `page_protocol.json`（8 种版式 + 4 种主题），引擎按协议渲染：

```bash
# 直接调 main.py
python main.py protocol \
    --input /tmp/coze_uploads/page_protocol.json \
    --skip-bg-gen

# 或用 coze_runner.py 一键
python coze_runner.py --mode protocol \
    --name "安岳鞋服加工园区" \
    --input /tmp/coze_uploads/page_protocol.json
# → {"success": true, "pdf_path": "...", "size_kb": ..., "mode": "protocol"}
```

**协议 8 种版式**：

| type | 用途 | 必填字段 |
|------|------|---------|
| `cover` | 封面 | title, subtitle |
| `closing` | 结尾 | thanks_title |
| `toc` | 目录 | chapters[] |
| `chapter-divider` | 章节过渡 | chapter_num, chapter_title |
| `image-text-split` | 图文分栏 | title, content.bullets[] |
| `three-cards` | 三概念卡 | title, cards[] |
| `comparison-table` | 方案对比 | title, table.headers[], table.rows[] |
| `data-profile` | 数据画像 | title, dimensions[] |

**4 种主题**：`blue-grey-business` / `dark-tech` / `warm-paper` / `green-eco`

协议规范详见 `ppt-layout-protocol-v1.md`。适配器自动将 8 种协议版式映射到引擎 17 种模板，无需手写 deck.yaml。

## 引擎内部流程（供参考）

```
main.py build
  │
  ├─ 1. copy_renders()              复制效果图 → assets/images/renders/
  ├─ 2. parse_v2_pdf.py             参考 PDF → deck.yaml (骨架)
  ├─ 3. fill_from_ref_pdf.py        参考 PDF 每页文字+分析图 → 回填 deck.yaml ★成果版关键
  ├─ 4. parse_coze_md.py (可选)     MD 草稿 → 回填概念主旨
  ├─ 5. parse_excel.py  (可选)     Excel → 回填指标页
  ├─ 6. fill_content.py             章节要点 → 均分填页
  ├─ 7. gen_bg.py (可选)           分析 deck.yaml 文本→封面+每章意向图 (--skip-bg-gen 跳过)
  │                                · 项目类型识别: 冷链/鞋服/物流/产业园/住宅/商业 → 封面场景
  │                                · 章节名映射: 场地→鸟瞰 市场→城市 概念→抽象 方案→渲染
  │                                ·              分析→流线 二期→远景 图纸→蓝图 说明→材质
  │                                · 输出 assets/images/bg/cover.jpg + divider_chNN.jpg 每章独立
  ├─ 8. render_slide.py --all       deck.yaml + templates → slides/*.html
  └─ 9. build_pdf.py                slides/*.html + base.css → PDF
```

## 常见问题

**Q: COZE 沙箱里 PDF 渲染黑屏？**
A: `playwright install chromium` 没跑。跑一次即可，chromium 会被 Playwright 缓存到用户目录。

**Q: 效果图没显示？**
A: 检查 `deck.yaml` 对应 slide 的 `data.image` 字段是否是相对路径如 `../assets/images/renders/鸟瞰1.png`。如果是绝对路径或路径不对，改成相对路径。

**Q: 文字是乱码？**
A: 检查 COZE 写入素材时的编码——统一 UTF-8。Excel 默认也是 UTF-8。

**Q: DXF 数据怎么抽？**
A: 当前引擎只做 `ezdxf.open(dxf_path)` 验证能读，不抓具体字段。后续需要在 `parse_v2_pdf.py` 里加 DXF 解析函数，把图层坐标/面积/层高注入 deck.yaml 对应页。

## 版本

v1.0 · 2026-09-20
