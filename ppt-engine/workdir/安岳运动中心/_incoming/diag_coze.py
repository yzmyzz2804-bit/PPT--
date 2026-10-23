# -*- coding: utf-8 -*-
"""临时: 打印态 HTML 的定位诊断"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PRINT_HTML = ROOT / 'build' / 'coze_print.html'

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, channel='chrome')
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 800})
    page.goto(PRINT_HTML.as_uri())
    page.wait_for_timeout(500)
    info = page.evaluate("""() => {
      const g = (el, ps) => { const s = getComputedStyle(el); const o = {};
        ps.forEach(k => o[k] = s[k]); return o; };
      const stage = document.getElementById('stage');
      const deck = document.getElementById('deck');
      const out = {
        stage: g(stage, ['position','display','inset','height']),
        deck: g(deck, ['position','display','width','height','transform']),
        slides: [...document.querySelectorAll('section.slide')].map((el,i) => ({
          i: i+1, cls: el.className, inline: el.getAttribute('style'),
          cs: g(el, ['position','inset','width','height','display','opacity','visibility','transform','margin'])
        }))
      };
      return out;
    }""")
    print('stage:', info['stage'])
    print('deck :', info['deck'])
    for s in info['slides']:
        print(s['i'], s['cls'], '| inline=', s['inline'])
        print('    ', s['cs'])
    browser.close()
