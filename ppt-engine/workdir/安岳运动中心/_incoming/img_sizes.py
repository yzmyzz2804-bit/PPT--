# -*- coding: utf-8 -*-
import io, base64, re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / 'source' / 'coze_浅色版_原始.html').read_text(encoding='utf-8')
secs = re.findall(r'<section class="slide[^"]*">.*?</section>', html, re.S)
for i, sec in enumerate(secs, 1):
    srcs = re.findall(r'src="data:image/(\w+);base64,([^"]+)"', sec)
    for t, d in srcs:
        im = Image.open(io.BytesIO(base64.b64decode(d)))
        print(f'p{i:02d} {t} {im.size} ratio={im.size[0]/im.size[1]:.2f} bytes={len(d)//1024}KB')
