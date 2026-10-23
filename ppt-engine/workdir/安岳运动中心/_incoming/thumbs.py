# -*- coding: utf-8 -*-
"""导出 PDF 缩略图 + 逐页显著像素统计, 用于验收空白/错位"""
import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'build' / '安岳运动中心_v6_浅色版.pdf'
out = ROOT / 'build' / '_diag_coze'
out.mkdir(parents=True, exist_ok=True)
for f in out.glob('*.png'):
    f.unlink()

doc = fitz.open(pdf)
print('pages =', doc.page_count)
for i, page in enumerate(doc):
    r = page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(0.55, 0.55))
    pix.save(str(out / f'p{i+1:02d}.png'))
    # 采样非白像素占比(粗判是否空白)
    import collections
    small = page.get_pixmap(matrix=fitz.Matrix(0.06, 0.06))
    n = small.width * small.height
    samples = small.samples
    nonwhite = 0
    for j in range(0, len(samples), small.n):
        if samples[j] < 240 or samples[j+1] < 240 or samples[j+2] < 240:
            nonwhite += 1
    print(f'  p{i+1:02d}: {r.width:.0f}x{r.height:.0f}  nonzero={nonwhite*100//max(n,1)}%')
doc.close()
print('shots ->', out)
