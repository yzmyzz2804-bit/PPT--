# -*- coding: utf-8 -*-
"""诊断 slide 9(.plan) 在单页打印态下的 flex 高度分配"""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'source' / 'coze_浅色版_原始.html'
import importlib.util
spec = importlib.util.spec_from_file_location('b', ROOT / 'build_coze_pdf.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

html = SRC.read_text(encoding='utf-8')
head = html[: html.index('</head>')]
secs = re.findall(r'<section class="slide[^"]*">.*?</section>', html, re.S)
tmp = ROOT / 'build' / '_dbg'
tmp.mkdir(parents=True, exist_ok=True)
f = tmp / 's09.html'
f.write_text(f'{head}<style>{b.PER_PAGE}</style>\n</head>\n<body>\n<div id="stage"><div id="deck">\n{secs[8]}\n</div></div>\n</body>\n</html>', encoding='utf-8')

with sync_playwright() as p:
    try:
        br = p.chromium.launch(headless=True, channel='chrome')
    except Exception:
        br = p.chromium.launch(headless=True)
    pg = br.new_page(viewport={'width': 1280, 'height': 720})
    pg.goto(f.as_uri())
    pg.wait_for_load_state('load')
    pg.wait_for_timeout(500)
    out = pg.evaluate("""() => {
      const g=(el)=>{const s=getComputedStyle(el);const r=el.getBoundingClientRect();
        return {pos:s.position,h:Math.round(r.height),w:Math.round(r.width),
                minH:s.minHeight,flex:s.flex,overflow:s.overflow,mxH:s.maxHeight};};
      const q=(sel)=>{const e=document.querySelector(sel);return e?g(e):null;};
      return {slide:q('section.slide'), plan:q('.plan'), imgwrap:q('.plan .imgwrap'),
              img:q('.plan img'), leg:q('.plan .leg'),
              legTop: (document.querySelector('.plan .leg')||{}).getBoundingClientRect ?
                      Math.round(document.querySelector('.plan .leg').getBoundingClientRect().top) : null};
    }""")
    for k, v in out.items():
        print(k, v)
    br.close()
