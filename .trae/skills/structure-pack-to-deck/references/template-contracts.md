# ppt-engine 模板数据契约与已知坑

9 个模板按文件名自动发现（无注册表）。占位符语法：`{{var}}`、`{{#arr}}{{/arr}}`、`{{^x}}{{/x}}`（反义段）；空元素用 `:empty` 隐藏；`:has()` 选择器 Chromium 渲染可用。

## 布局基线 (base.css)

- `.slide` 1920×1080 overflow:hidden
- `.slide-content` 绝对定位 top260 / left80 / right80 / bottom80
- `.page-header` top120 / left80；`.brand-mark` top50 / left60；`.page-number` bottom40 / right60
- 渲染器按 `slide.chapter` 注入 `--ch-accent` 分章色，build_pdf.py 已做 `#pg-NN` 页级作用域隔离

## 各模板契约

### cover
- 字段：`title`(可长，48px 自动换行)、`subtitle`、`meta`(单位/日期等)、`bg_image`
- 无 bg 时 footer 白字自动改深色（`:not(:has(.bg-layer))` 分支）

### closing
- 字段：`thanks_title`、`thanks_subtitle`、`concept_recap`、`bg_image`

### split-image-text (image-text-split)
- 字段：`title`、`subtitle`、`image`、`image_caption`、`bullets[]`、`key_metrics[]`、`callout{text,label}`
- bullets 可拼单卡用 `<br>` 连接；key_metrics 拼"核心指标"卡；无 bullets 时用 callout 做"核心定位"卡
- 缺图自动出 `.ph-frame` 蓝色虚线占位相框

### multi-card-row (three-cards / data-profile)
- `data_cards[]`: `number/unit/label/items[{key,val}]`；number/unit 空则隐藏，纯文字卡垂直居中（`:empty` + `:has()`）
- `photo_cards[]`: `image/title/tag`，渲染在数据卡下方一行（flex:1, min-height 240px）
- `bg_image` 支持：整页底图 + 深色遮罩，白卡浮于其上
- 曾有 bug：模板把内容容器改成 relative+z-index 导致 base.css 80px 页边距失效、卡片出血——修复后仅保留 z-index:3

### compare-table (comparison-table)
- 固定 3 列：`headers.0/1/2`，列宽 26/36/38%
- 行：`indicator` / `b`(热列，`b_better: true` 时加 `◂` 标记) / `note`
- 底部 `summary_cards[]`: `name/items[{k,v}]/hot`——结论卡字段名是 k/v
- 4 列表压缩：`headers[1]=='原规划'` 类对比表 → `[h0, h2, "h1 / h3"]` + note=`原值（变化）`；通用 4 列 → `[h0, h1, "h2 / h3"]` + note=`r2<br>r3`

### chapter-divider-a / b / c
- a：左侧 45% 底图 + 右色块，支持 `bg_image`
- b：纯排版超大数字章号（无图）
- c：摘要型，必填 `points: [{num,title,desc}]` 4 条
- 共同字段：`chapter_num`(字符串"03")、`chapter_title`、`chapter_desc`、`chapter_concept`(英文)
- 页数据自带 `chapter_num`，页码重排时必须同步改

## 引擎命令

```
python ppt-engine/main.py render --project <dir>      # slides/*.html
python ppt-engine/main.py pdf --project <dir> --out <pdf>
```

- 渲染器自带图片体检 `null_missing_images()`：不存在的 `../assets/...` 路径置空 → 模板统一出占位相框
- 缩略图：pymupdf `page.get_pixmap(matrix=Matrix(0.42,0.42))` → `build/_diag/pNN.png`
- shell 末尾 CLIXML/PSSecurityException 输出是 PowerShell 执行策略噪音，忽略

## 分章色 (theme.json chapter_colors)

ch1 海军蓝 #0E2A5B / ch2 深青 #1B5E7E / ch3 古铜金 #8B6914 / ch4 赤陶 #8A4B26 / ch5 松绿 #2D5F5D / ch6 蓝灰 #46526B / ch7 石墨灰 / ch8 回蓝。删章后章号顺移会导致颜色轮换，属正常现象。
