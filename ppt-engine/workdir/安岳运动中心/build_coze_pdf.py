# -*- coding: utf-8 -*-
"""
build_coze_pdf.py — 把 Coze「浅色版」自包含 deck(1280×720 翻页态) 转成 12 页 PDF

输入: source/coze_浅色版_原始.html (cover + 10 内容 + closing, 图片 base64 内嵌)
输出: build/安岳运动中心_v6_浅色版.pdf

做法(确定性, 规避分页漂移):
  1) 剥离原页面的 JS 轮播脚本(它会把非 .active 页设为不可见)
  2) 拆出 12 个 <section class="slide">, 每页单独生成一个只含该页的 HTML
  3) 逐页 page.pdf(1280×720) 得到单页 PDF, 再用 pymupdf 合并
  -> 每页严格 1 张 slide 占满 1280×720, 不会再叠压/串页
其它修正:
  - 解除"只有 .active 才可见"限制 -> 全部常显
  - kicker 页码按顺序重排 01..10(原 deck 中 LIFECYCLE / MECHANISM 两页都写 06)
  - .plan .imgwrap 补 min-height:0, 否则大图把图例 .leg 挤出画面
"""
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'source' / 'coze_浅色版_原始.html'
BUILD = ROOT / 'build'
OUT_PDF = BUILD / '安岳运动中心_v6_浅色版.pdf'

PER_PAGE = """
/* —— 单页打印态(由 build_coze_pdf.py 注入) —— */
html, body { height: 720px !important; max-height: 720px !important;
             overflow: hidden !important; background: #fff !important; margin: 0 !important; }
#stage { position: static !important; inset: auto !important; display: block !important; }
#deck { position: relative !important; width: 1280px !important; height: 720px !important;
        overflow: hidden !important;
        box-shadow: none !important; transform: none !important; background: #fff !important; }
.slide, .slide.active {
  position: absolute !important; inset: 0 !important;
  opacity: 1 !important; visibility: visible !important;
}
.plan, .plan .imgwrap { min-height: 0 !important; }
.plan { align-items: center; }
.plan .imgwrap { width: auto; }
.plan .leg { justify-content: center; }
@media print {
  @page { size: 1280px 720px; margin: 0; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
"""


def renumber(section: str, counter: dict) -> str:
    """kicker 页码按出现顺序重排 01..N(修原 deck 重复的 06)"""
    def repl(_m):
        counter['n'] += 1
        return f'<span class="num">{counter["n"]:02d}</span>'
    return re.sub(r'<span class="num">\d{1,2}</span>', repl, section)


def main():
    if not SRC.exists():
        sys.exit(f'✗ 找不到源文件: {SRC}')
    html = SRC.read_text(encoding='utf-8')
    head = html[: html.index('</head>')]                       # 保留 <head>+全部样式
    sections = re.findall(r'<section class="slide[^"]*">.*?</section>', html, re.S)
    if not sections:
        sys.exit('✗ 未解析到任何 <section class="slide">')
    counter = {'n': 0}
    sections = [renumber(s, counter) for s in sections]

    BUILD.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='coze_pg_'))

    from playwright.sync_api import sync_playwright
    parts = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, channel='chrome')
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        for i, sec in enumerate(sections, 1):
            html_i = f'{head}<style>{PER_PAGE}</style>\n</head>\n<body>\n<div id="stage"><div id="deck">\n{sec}\n</div></div>\n</body>\n</html>'
            f_in = tmp / f's{i:02d}.html'
            f_in.write_text(html_i, encoding='utf-8')
            f_pdf = tmp / f's{i:02d}.pdf'
            page.goto(f_in.as_uri())
            page.wait_for_load_state('load')
            page.wait_for_timeout(400)
            page.pdf(path=str(f_pdf), width='1280px', height='720px',
                     print_background=True,
                     margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
            parts.append(f_pdf)
        browser.close()

    import pymupdf
    merged = pymupdf.open()
    for f in parts:
        d = pymupdf.open(str(f))
        merged.insert_pdf(d, from_page=0, to_page=0)   # 只取首屏, 杜绝溢出产生的空第 2 页
        d.close()
    merged.save(str(OUT_PDF))
    n_pages = merged.page_count
    merged.close()

    for f in tmp.glob('*'):
        f.unlink()
    tmp.rmdir()

    print(f'✓ PDF: {OUT_PDF}  slides={len(sections)}  pages={n_pages}')


if __name__ == '__main__':
    main()
