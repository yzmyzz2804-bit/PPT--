"""
build_pdf.py - 组合所有 slides/*.html 为单一 HTML,通过 Playwright 渲染 PDF

依赖:
    pip install playwright pyyaml
    playwright install chromium

使用:
    python build_pdf.py                      # 默认输出 build/deck.pdf
    python build_pdf.py --output out.pdf
"""
import sys
import re
import argparse
import yaml
from pathlib import Path



from _env import ENGINE_ROOT, PROJECT_ROOT, DECK_PATH, SLIDES_DIR, BUILD_DIR

def extract_body(html: str) -> str:
    """从单页 HTML 中提取 <body> 内的 .slide 节点"""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if not body_match:
        return html
    return body_match.group(1).strip()


def extract_head_styles(html: str) -> str:
    """提取 <style> 块(每页专属样式)"""
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    return '\n'.join(styles)


def scope_css(css: str, scope: str) -> str:
    """给每条 CSS 规则的选择器加唯一前缀(#pg-NN),实现页间样式隔离。

    背景: 同模板页(如各章 chapter-divider)的 <style> 使用同名类
    (.slide-chapter .photo-left .bg),直接合并进 deck.html 时 CSS 层叠
    "最后定义者胜",导致所有章节分隔页都显示最后一章的背景图。
    :root 主题变量块各页相同,提取后全局保留,不加前缀。
    """
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)  # 去注释防污染选择器
    root_blocks = re.findall(r':root\s*\{[^{}]*\}', css)
    css = re.sub(r':root\s*\{[^{}]*\}', '', css)

    # 分章色等"每页不同"的变量不能留在全局 :root(会被最后一页覆盖),
    # 改写为页级作用域 #pg-NN { --ch-accent: ... },靠继承作用于本页
    scoped_vars = []
    clean_roots = []
    for rb in root_blocks:
        m = re.search(r'--ch-accent\s*:\s*([^;]+);', rb)
        if m:
            scoped_vars.append(f'{scope} {{ --ch-accent: {m.group(1).strip()}; }}')
            rb = re.sub(r'--ch-accent\s*:\s*[^;]+;', '', rb)
        clean_roots.append(rb)

    out = []
    i, n = 0, len(css)
    while i < n:
        brace = css.find('{', i)
        if brace == -1:
            break
        selector = css[i:brace].strip()
        depth, j = 1, brace + 1
        while j < n and depth:
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
            j += 1
        body = css[brace + 1:j - 1]
        if selector:
            if selector.startswith('@media'):
                out.append(f'{selector}{{{scope_css(body, scope)}}}')
            else:
                parts = [f'{scope} {p.strip()}'
                         for p in selector.split(',') if p.strip()]
                out.append(', '.join(parts) + ' {' + body.strip() + '}')
        i = j
    return '\n'.join(clean_roots + scoped_vars + out)


def assemble_deck_html(deck: dict) -> str:
    """组装完整 deck HTML: 头部 + 每页 body + base.css + 打印 CSS"""
    slides = deck.get('slides', [])
    if not slides:
        print('✗ deck.yaml 中没有 slides')
        sys.exit(1)

    bodies = []
    styles = []
    for idx, s in enumerate(slides):
        slide_path = SLIDES_DIR / f'{s["id"]}.html'
        if not slide_path.exists():
            print(f'  ⚠ 跳过未渲染页: {s["id"]} (请先运行 render_slide.py)')
            continue
        html = slide_path.read_text(encoding='utf-8')
        # 每页 body 包进唯一 id 的包裹层,使本页样式限定作用域,
        # 杜绝同模板页(如各章分隔页)同名类在合并后互相覆盖
        page_id = f'pg-{idx:02d}'
        body = f'<div id="{page_id}">\n{extract_body(html)}\n</div>'
        bodies.append(body)
        styles.append(f'/* —— {s["id"]} —— */\n{scope_css(extract_head_styles(html), f"#{page_id}")}')

    base_css_path = ENGINE_ROOT / 'base.css'
    base_css = base_css_path.read_text(encoding='utf-8') if base_css_path.exists() else ''

    project_name = deck.get('project', {}).get('name', 'PPT 概念方案')
    project_name_en = deck.get('project', {}).get('name_en', '')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1920, initial-scale=1">
<title>{project_name}</title>
<style>
{base_css}

/* —— 各页专属样式 —— */
{chr(10).join(styles)}

@media print {{
  @page {{
    size: 1920px 1080px;
    margin: 0;
  }}
  body {{ background: #fff; margin: 0; padding: 0; }}
  .slide {{
    margin: 0;
    box-shadow: none;
    page-break-after: always;
    page-break-inside: avoid;
  }}
  .slide:last-child {{ page-break-after: auto; }}
  * {{
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
}}
</style>
</head>
<body>
{chr(10).join(bodies)}
</body>
</html>
"""


def render_pdf(deck_html: str, output_path: Path):
    """调用 Playwright 渲染 PDF"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('✗ 需要 playwright: pip install playwright && playwright install chromium')
        sys.exit(1)

    # 先把 deck html 写到 build/deck.html (便于调试)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    debug_path = BUILD_DIR / 'deck.html'
    debug_path.write_text(deck_html, encoding='utf-8')

    with sync_playwright() as p:
        # 优先用系统 Chrome(无需下载 chromium),没有则回退到 chromium
        try:
            browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(debug_path.as_uri())
        page.pdf(
            path=str(output_path),
            width='1920px',
            height='1080px',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        browser.close()
    print(f'✓ PDF 已生成: {output_path}')


def main():
    ap = argparse.ArgumentParser(description='构建 PDF')
    ap.add_argument('--output', default='', help='输出 PDF 路径')
    args = ap.parse_args()

    if not DECK_PATH.exists():
        print(f'✗ deck.yaml 不存在')
        sys.exit(1)

    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    deck_html = assemble_deck_html(deck)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.output) if args.output else BUILD_DIR / f'{deck.get("project", {}).get("name", "deck")}.pdf'

    render_pdf(deck_html, out)

    # 更新 deck.yaml 构建时间戳
    from datetime import datetime
    deck.setdefault('build', {})
    deck['build']['last_build'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    deck['build']['last_build_pdf'] = str(out)
    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


if __name__ == '__main__':
    main()
