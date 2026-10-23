---
name: dual-layout-qa
description: 需要生成或检查现场汇报与纸面阅读两个版本时，按共同内容模型分别排版并检查一致性。
---

# dual-layout-qa


1. 先读config/layout_profiles.json和批准deck，确认既有版式是否允许reflow。
2. reporting默认16:9，正文24pt；print_a3横向A3 420×297mm，正文14pt，标签与来源12pt；这些是项目默认，实际字体与预览须核。
3. 一页一个信息任务而不是强制图表，关键claim在所有请求版本保留，可调整页数和解释深度。
4. 先检查安装字体和实际输出，溢出不能直接缩小字号；保护图片裁切/重绘/替换先审批。
5. 逐页检查结构、数字、视觉、跨版、审批、交付；没有视觉工具则not_checked，不声称已通过。
6. 打印实际纸面与灰度检查，print_same_slides不能当成A3重排。报告按schemas/qa.schema.json。
