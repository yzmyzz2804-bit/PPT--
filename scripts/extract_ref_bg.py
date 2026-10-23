"""
extract_ref_bg.py - 从参考 v2.pdf 提取封面+各章分隔页全幅背景图
(API 故障期间的恢复方案; API 恢复后可用 gen_bg.py 重新生成替换)
"""
import re
import yaml
import pymupdf
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
BG_DIR = PROJECT_ROOT / 'assets' / 'images' / 'bg'
REF_PDF = Path(r'E:\TRAE\l-柠檬冷链物流\20260920合--安岳县柠檬冷链共享仓建设项目v2.pdf')

doc = pymupdf.open(REF_PDF)
BG_DIR.mkdir(parents=True, exist_ok=True)


def extract_full_image(page, out: Path) -> bool:
    """提取页面上占面积最大的图(全幅背景), 渲染裁剪 2x"""
    infos = page.get_image_info(xrefs=True)
    if not infos:
        return False
    pa = page.rect.width * page.rect.height
    best, area = None, 0
    for info in infos:
        b = info['bbox']
        a = (b[2] - b[0]) * (b[3] - b[1])
        if a > area:
            best, area = b, a
    if best is None or area < pa * 0.5:  # 至少占半页才算背景图
        return False
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(best))
    pix.save(str(out))
    print(f'  ✓ {out.name} ({out.stat().st_size // 1024} KB, bbox={best})')
    return True


# 1. 封面 (ref p1)
print('== 封面 ==')
extract_full_image(doc[0], BG_DIR / 'cover.jpg')

# 2. 各章分隔页
deck = yaml.safe_load(DECK_PATH.read_text(encoding='utf-8'))
print('== 章节分隔页 ==')
ch_updated = 0
for s in deck['slides']:
    if s['template'] != 'chapter-divider':
        continue
    pno = int(re.match(r'slide_(\d+)', s['id']).group(1))
    if pno > len(doc):
        continue
    num = s['data'].get('chapter_num', f'{pno:02d}')
    out = BG_DIR / f'divider_ch{num}.jpg'
    ok = extract_full_image(doc[pno - 1], out)
    if ok:
        s['data']['bg_image'] = f'../assets/images/bg/divider_ch{num}.jpg'
        ch_updated += 1
    else:
        print(f'  ⚠ p{pno} 无全幅背景图,保留 {s["data"].get("bg_image")}')

# 封面 bg_image 保险复位
for s in deck['slides']:
    if s['template'] == 'cover':
        s['data']['bg_image'] = '../assets/images/bg/cover.jpg'

DECK_PATH.write_text(
    yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
    encoding='utf-8')
print(f'\n[OK] 分隔页 bg_image 更新 {ch_updated} 张; cover.jpg 已就位')
