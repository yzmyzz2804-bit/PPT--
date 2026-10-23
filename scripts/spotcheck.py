"""验收: PDF 页数/大小 + 抽查关键页渲染 PNG"""
import pymupdf
from pathlib import Path

pdf = Path(r'e:\TRAE\PPT概念规划设计\build\安岳县柠檬冷链共享仓建设项目.pdf')
doc = pymupdf.open(pdf)
print(f'页数: {len(doc)} | 大小: {pdf.stat().st_size // 1024} KB')

# 抽查页: 25(指标) 27(功能分析) 40(立面) 49(图纸)
outdir = Path(r'e:\TRAE\PPT概念规划设计\build\spotcheck')
outdir.mkdir(exist_ok=True)
for pno in [25, 27, 40, 49]:
    page = doc[pno - 1]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(0.75, 0.75))
    out = outdir / f'new_p{pno}.png'
    pix.save(str(out))
    # 同页文字首几行
    text = [l.strip() for l in page.get_text().splitlines() if l.strip()]
    print(f'p{pno}: {" | ".join(text[:4])[:70]}')
    print(f'   → {out.name}')

# 检查 SCHEME 残留
for i, page in enumerate(doc, 1):
    t = page.get_text()
    if 'SCHEME' in t and i >= 49:
        print(f'⚠ p{i} 仍有 SCHEME 残留')
print('抽查完成')
