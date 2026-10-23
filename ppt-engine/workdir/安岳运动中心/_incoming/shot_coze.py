# -*- coding: utf-8 -*-
"""临时: 对 coze_print.html 逐页元素截图, 用于判断问题出在屏幕布局还是打印"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PRINT_HTML = ROOT / 'build' / 'coze_print.html'
OUT = ROOT / 'build' / '_shots'
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, channel='chrome')
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 800})
    page.goto(PRINT_HTML.as_uri())
    page.wait_for_timeout(800)
    slides = page.locator('section.slide')
    n = slides.count()
    for i in range(n):
        bb = slides.nth(i).bounding_box()
        print(f'  slide {i+1}: box={bb}')
        slides.nth(i).screenshot(path=str(OUT / f's{i+1:02d}.png'))
    print('total', n)
    browser.close()
