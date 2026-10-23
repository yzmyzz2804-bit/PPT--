"""
PPT 概念生成引擎 - HTML生成辅助工具
生成高端商务风 HTML PPT 的 CSS 模板
"""

def generate_style_css(brand_primary='#0E2A5B', brand_light='#2562EB', bg_base='#FFFFFF', text_main='#0E2A5B', text_secondary='#94A2B8'):
    """生成高端商务风 PPT 样式"""
    return f"""
:root {{
  --brand-primary: {brand_primary};
  --brand-light: {brand_light};
  --text-main: {text_main};
  --text-secondary: {text_secondary};
  --border-color: #E2E7F0;
  --divider-color: #CBD5E1;
  --bg-base: {bg_base};
  --bg-secondary: #F7FAFB;
  --bg-tertiary: #F1F5F9;
  --font-cn: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  --font-en: "Arial", "Helvetica", "Inter", sans-serif;
  --font-num: "Arial", "Helvetica", "Inter", sans-serif;
  --slide-w: 1920px;
  --slide-h: 1080px;
  --radius: 6px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: var(--font-cn);
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-main);
  background: #e8ecf0;
  -webkit-font-smoothing: antialiased;
}}

.slide {{
  position: relative;
  width: var(--slide-w);
  height: var(--slide-h);
  background: var(--bg-base);
  overflow: hidden;
  margin: 40px auto;
  box-shadow: 0 4px 32px rgba(0,0,0,0.08);
}}

/* 品牌标识 */
.brand-mark {{
  position: absolute;
  top: 50px;
  left: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 10;
}}
.brand-mark .square {{
  width: 14px;
  height: 14px;
  background: var(--divider-color);
}}
.brand-mark .line {{
  width: 36px;
  height: 2px;
  background: var(--divider-color);
}}
.brand-mark .text {{
  font-family: var(--font-en);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--text-secondary);
}}

/* 页面标题区 */
.page-header {{
  position: absolute;
  top: 120px;
  left: 80px;
  right: 80px;
  z-index: 5;
}}
.page-tag {{
  font-family: var(--font-en);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 2px;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 8px;
}}
.page-title {{
  font-size: 36px;
  font-weight: 700;
  color: var(--brand-primary);
  line-height: 1.3;
  margin-bottom: 8px;
}}
.page-subtitle {{
  font-family: var(--font-en);
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}}
.title-line {{
  width: 36px;
  height: 3px;
  background: var(--brand-light);
  margin-top: 20px;
}}

/* 内容区域 */
.slide-content {{
  position: absolute;
  top: 260px;
  left: 80px;
  right: 80px;
  bottom: 80px;
  z-index: 2;
}}

/* 卡片 */
.card {{
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 24px;
  position: relative;
  transition: all 0.3s ease;
}}
.card:hover {{
  border-color: var(--brand-light);
  box-shadow: 0 4px 16px rgba(37, 98, 235, 0.08);
}}
.card-accent-top::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--brand-light);
  border-radius: var(--radius) var(--radius) 0 0;
}}
.card-accent-left::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 4px;
  background: var(--brand-light);
  border-radius: var(--radius) 0 0 var(--radius);
}}
.card-title {{
  font-size: 20px;
  font-weight: 700;
  color: var(--brand-primary);
  margin-bottom: 16px;
}}
.card-text {{
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-main);
  opacity: 0.85;
}}

/* 数据卡片 */
.data-card {{
  text-align: center;
  padding: 28px 20px;
}}
.data-number {{
  font-family: var(--font-num);
  font-size: 48px;
  font-weight: 700;
  color: var(--brand-primary);
  line-height: 1;
  margin-bottom: 8px;
}}
.data-unit {{
  font-family: var(--font-en);
  font-size: 14px;
  color: var(--text-secondary);
}}
.data-label {{
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin-top: 12px;
}}
.data-items {{
  margin-top: 16px;
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
}}
.data-item {{
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}}
.data-item-key {{ color: var(--text-secondary); }}
.data-item-val {{ font-family: var(--font-num); font-weight: 600; color: var(--text-main); }}

/* 照片卡片 */
.photo-card {{
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
}}
.photo-card img {{
  width: 100%;
  height: 180px;
  object-fit: cover;
  display: block;
}}
.photo-caption {{
  padding: 14px 18px;
  background: var(--bg-secondary);
}}
.photo-title {{
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}}
.photo-tag {{
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-en);
}}

/* 图文分栏 */
.split-layout {{
  display: flex;
  gap: 48px;
  height: 100%;
}}
.split-left {{
  width: 58%;
  position: relative;
}}
.split-left img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: var(--radius);
}}
.split-right {{
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}}

/* 章节过渡页 */
.slide-chapter {{
  display: flex;
  background: var(--bg-base);
}}
.chapter-left {{
  width: 45%;
  background: var(--brand-primary);
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 80px 60px;
  color: #fff;
}}
.chapter-left::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0,0,0,0.1) 0%, transparent 60%);
}}
.chapter-num {{
  font-family: var(--font-en);
  font-size: 200px;
  font-weight: 700;
  opacity: 0.1;
  line-height: 1;
  position: absolute;
  top: 60px;
  right: 40px;
}}
.chapter-cn {{
  font-size: 48px;
  font-weight: 700;
  position: relative;
  z-index: 2;
  margin-bottom: 12px;
}}
.chapter-en {{
  font-family: var(--font-en);
  font-size: 16px;
  letter-spacing: 2px;
  opacity: 0.7;
  position: relative;
  z-index: 2;
}}
.chapter-right {{
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
}}
.chapter-right-en {{
  font-family: var(--font-en);
  font-size: 32px;
  font-weight: 700;
  color: var(--brand-primary);
  letter-spacing: 2px;
  line-height: 1.3;
  text-align: center;
}}

/* 封面 */
.slide-cover {{
  background: var(--brand-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 120px;
}}
.cover-content {{
  width: 50%;
  text-align: right;
  position: relative;
  z-index: 2;
}}
.cover-main {{
  font-size: 72px;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 24px;
  position: relative;
  display: inline-block;
}}
.cover-main::before,
.cover-main::after {{
  content: '';
  position: absolute;
  top: 50%;
  width: 60px;
  height: 2px;
  background: #fff;
  opacity: 0.5;
}}
.cover-main::before {{ right: calc(100% + 20px); }}
.cover-main::after {{ left: calc(100% + 20px); }}
.cover-sub {{
  font-family: var(--font-en);
  font-size: 20px;
  font-weight: 400;
  opacity: 0.7;
  letter-spacing: 2px;
  margin-bottom: 60px;
}}
.cover-project {{
  font-size: 20px;
  margin-bottom: 8px;
  opacity: 0.9;
}}
.cover-date {{
  font-family: var(--font-en);
  font-size: 14px;
  opacity: 0.6;
}}

/* 目录页 */
.slide-toc {{
  padding: 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}
.toc-title {{
  font-family: var(--font-en);
  font-size: 18px;
  letter-spacing: 4px;
  color: var(--text-secondary);
  margin-bottom: 60px;
}}
.toc-list {{
  list-style: none;
}}
.toc-item {{
  display: flex;
  align-items: center;
  padding: 24px 0;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}}
.toc-item::before {{
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--brand-light);
  opacity: 0.6;
}}
.toc-num {{
  font-family: var(--font-en);
  font-size: 36px;
  font-weight: 700;
  color: var(--brand-primary);
  width: 80px;
  opacity: 0.8;
}}
.toc-info {{
  flex: 1;
  padding-left: 20px;
}}
.toc-name {{
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}}
.toc-en {{
  font-family: var(--font-en);
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 1px;
}}
.toc-pages {{
  font-family: var(--font-en);
  font-size: 14px;
  color: var(--text-secondary);
}}

/* 四象限布局 */
.grid-2x2 {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}

/* 方案对比 */
.compare-layout {{
  display: flex;
  gap: 32px;
  height: 100%;
}}
.compare-col {{
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 32px;
  position: relative;
}}
.compare-col.featured {{
  border-color: var(--brand-light);
  border-width: 2px;
}}
.compare-title {{
  font-size: 24px;
  font-weight: 700;
  color: var(--brand-primary);
  margin-bottom: 12px;
}}
.compare-subtitle {{
  font-family: var(--font-en);
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 1px;
  margin-bottom: 24px;
}}
.compare-items {{
  list-style: none;
}}
.compare-item {{
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 14px;
  display: flex;
  justify-content: space-between;
}}
.compare-item:last-child {{ border-bottom: none; }}
.compare-item-key {{ color: var(--text-secondary); }}
.compare-item-val {{ font-weight: 600; font-family: var(--font-num); }}

/* 结尾页 */
.slide-closing {{
  background: var(--brand-primary);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}}
.closing-text {{
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 20px;
}}
.closing-sub {{
  font-family: var(--font-en);
  font-size: 18px;
  opacity: 0.6;
  letter-spacing: 4px;
}}

/* 列表样式 */
.feature-list {{
  list-style: none;
}}
.feature-list li {{
  padding: 8px 0 8px 24px;
  position: relative;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-main);
  opacity: 0.85;
}}
.feature-list li::before {{
  content: '';
  position: absolute;
  left: 0;
  top: 16px;
  width: 8px;
  height: 8px;
  background: var(--brand-light);
  border-radius: 50%;
}}

/* 底部页码 */
.page-number {{
  position: absolute;
  bottom: 40px;
  right: 60px;
  font-family: var(--font-en);
  font-size: 13px;
  color: var(--text-secondary);
  z-index: 10;
}}
.page-number .current {{
  font-size: 20px;
  font-weight: 700;
  color: var(--brand-primary);
  margin-right: 4px;
}}
"""


def generate_html_structure(title, slides_html, style_css):
    """生成完整HTML文档"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{style_css}

@media print {{
  @page {{
    size: 1920px 1080px;
    margin: 0;
  }}
  body {{
    background: #fff;
    margin: 0;
    padding: 0;
  }}
  .slide {{
    margin: 0;
    box-shadow: none;
    page-break-after: always;
    page-break-inside: avoid;
  }}
  .slide:last-child {{
    page-break-after: auto;
  }}
  * {{
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
}}
</style>
</head>
<body>
{slides_html}
</body>
</html>
"""


if __name__ == '__main__':
    # 生成样式预览
    css = generate_style_css()
    print(f"生成样式 {len(css)} 字符")
