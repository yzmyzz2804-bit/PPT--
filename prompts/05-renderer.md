# 双版式渲染接口（ppt-engine 接入）

## 实际渲染后端

渲染引擎为 `ppt-engine/`（28 个 HTML 模板 + 5 个主题 + 13 个渲染脚本），不是抽象的"工具"。deck.yaml 每页契约：`{id, chapter, template, title, status, data, page_num}`，template 名直接对应 `ppt-engine/templates/*.html`。

系统 Chrome 已验证可用（`C:\Program Files\Google\Chrome\Application\chrome.exe`）；build_pdf.py 内置 `channel="chrome"` fallback，无需预装 playwright chromium。

## 具体调用

```bash
# 已有 deck.yaml 的项目全量重渲
python ppt-engine/main.py rebuild --project <项目目录>

# 只渲指定页（deck.yaml 已存在）
python ppt-engine/main.py re-render --project <项目目录> --slides 20,22,25

# 协议 v1.1 结构包（ZIP）→ deck.yaml → PDF
python ppt-engine/main.py protocol --input <page_protocol.json> --project <项目目录>

# 全流程（素材 → PDF 一把出）
python ppt-engine/main.py build --name <项目名> --ref-pdf <参考.pdf> --renders <效果图目录> --skip-bg-gen
```

## 双版式说明（reporting + print_a3）

reporting 16:9 与 print_a3 A3 横向 420×297mm 为同一 deck.yaml 的两个输出；渲染引擎原生 1280×720（16:9），A3 版式在模板层单独适配。参照 config/layout_profiles.json 和 docs/双版式版式规范对照表_A3与汇报版.xlsx。

## 工作流约束

1. 只在 04_render 阶段生成副本；保留原件，不重写 claims，不擅自替换/拉伸/裁切保护图片。
2. 同一事实按 claim_id 复用；格式可以不同，数值/单位/口径不变。
3. 检测字体实际存在；乱码/溢出先改非保护措辞或经批准拆页，不压到 minimum 以下。
4. 生成实际文件后核存在和非空，写 artifacts.json，绑定 deck SHA 及每个文件 SHA。
5. v7 强制：遵守 WORKBENCH_RULES_V7.md 及 L01—L09 对象门控；生产渲染前必须生成并校验 03_content/object_layout.json。禁止固定几何切块。
