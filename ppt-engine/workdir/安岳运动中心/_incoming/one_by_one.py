# -*- coding: utf-8 -*-
"""逐页隔离截图: 每次只显示 1 张 slide, 判断是"单页布局问题"还是"PDF 分页问题" """
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PRINT_HTML = ROOT / 'build' / 'coze_print.html'
OUT = ROOT / 'build' / '_one'
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob('*.png'):
    f.unlink()

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, channel='chrome')
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.goto(PRINT_HTML.as_uri())
    page.wait_for_load_state('load')
    page.wait_for_timeout(1500)
    n = page.locator('section.slide').count()
    for k in range(n):
        page.evaluate(
            """(k) => { document.querySelectorAll('section.slide').forEach((el,i)=>{
                 el.style.display = (i===k) ? 'flex' : 'none'; }); }""", k)
        page.wait_for_timeout(120)
        el = page.locator('section.slide').nth(k)
        el.screenshot(path=str(OUT / f's{k+1:02d}.png'))
    print('isolated shots ->', OUT, 'count', n)
    browser.close()
