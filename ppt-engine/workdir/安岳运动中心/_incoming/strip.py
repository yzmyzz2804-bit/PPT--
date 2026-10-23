# -*- coding: utf-8 -*-
"""临时: 剥离 Coze 自包含 deck 的 base64 图片, 抽出 CSS 供复刻参考"""
import re
from pathlib import Path

P = Path(__file__).resolve().parent
src = (P / 'coze_deck.html').read_text(encoding='utf-8')

stripped = re.sub(r'data:image/[^"\')]+', '[BASE64]', src)
(P / 'coze_deck_stripped.html').write_text(stripped, encoding='utf-8')

css = '\n\n/* ===== STYLE BLOCK ===== */\n'.join(
    re.findall(r'<style[^>]*>(.*?)</style>', src, re.S))
(P / 'coze_css.txt').write_text(css, encoding='utf-8')

print('stripped chars', len(stripped))
print('css chars', len(css))
print('style blocks', len(re.findall(r'<style[^>]*>', src)))
