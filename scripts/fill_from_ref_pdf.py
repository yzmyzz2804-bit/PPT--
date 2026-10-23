"""
fill_from_ref_pdf.py - 从参考 v2.pdf 抽取文字+图片,回填 deck.yaml 至成果版状态

对每页 NN: slide_NN ← ref pNN
  - 抽每页最大图片(渲染裁剪 2x) → assets/images/ref/pNN.png
  - 抽每页文字行(清洗) → 按模板回填:
      split-image-text  → cards[0].text (<br> 多行) + image
      multi-card-row    → photo_cards[0].image + data_cards[0].items
      quadrant-2x2      → quadrants[i].points 均分
      scheme-present    → description + image(空时) + 清 scheme_num
  - slide_25 compare-table: 按 Excel 验证过的原值修正(建筑密度 51.36% 等)

运行: python scripts/fill_from_ref_pdf.py <ref.pdf>
"""
import re
import sys
import shutil
from pathlib import Path

import fitz
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
REF_DIR = PROJECT_ROOT / 'assets' / 'images' / 'ref'

# 每页最多回填文字行数
MAX_LINES = 28
# 无效行模式: 纯英文/字母间距化/页码/过短
SKIP_RE = re.compile(r'^[A-Za-z\s·\-.,&0-9/():]*$')
# 页眉/章节杂词模式
HEADER_RES = [
    re.compile(r'^0\d\s*·'),            # "05 · 设计分析"
    re.compile(r'^第[一二三四五六七八九十]+章'),
    re.compile(r'^C\s*H\s*A\s*P\s*T\s*E\s*R'),
    re.compile(r'^C\s*O\s*N\s*T\s*E\s*N\s*T\s*S'),
]

PROJECT_NAME = ''


def clean_lines(page, slide_title: str) -> list:
    """抽取并清洗一页的文字行"""
    raw = page.get_text().strip()
    # title 变体: 原样 + 去编号("5.1 功能分析"→"功能分析")
    title_variants = {slide_title}
    m = re.match(r'^\d+\.\d+\s*', slide_title or '')
    if m:
        title_variants.add(slide_title[m.end():].strip())
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if len(ln) < 2:
            continue
        if ln in title_variants or ln == PROJECT_NAME:
            continue
        if any(p.match(ln) for p in HEADER_RES):
            continue
        # 全英文行(装饰性副标题) 跳过
        if SKIP_RE.match(ln) and not re.search(r'[\u4e00-\u9fff]', ln):
            continue
        # 纯数字/页码 跳过
        if re.match(r'^[\d\s/]+$', ln):
            continue
        lines.append(ln)
    # 去重保序
    seen, out = set(), []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    return out[:MAX_LINES]


def extract_largest_image(doc, page, pno: int) -> str:
    """导出页面上渲染面积最大的图片(裁剪渲染 2x), 返回相对路径或 ''"""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    infos = page.get_image_info(xrefs=True)
    if not infos:
        return ''
    pw, ph = page.rect.width, page.rect.height
    page_area = pw * ph
    best, best_area = None, 0
    for info in infos:
        bbox = info['bbox']
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        area = w * h
        # 过滤小 logo/装饰条: 面积占比 > 8% 且 尺寸 > 150pt
        if area > best_area and area > page_area * 0.08 and w > 150 and h > 150:
            best, best_area = bbox, area
    if best is None:
        return ''
    out = REF_DIR / f'p{pno:02d}.png'
    if out.exists():
        return f'../assets/images/ref/p{pno:02d}.png'
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(best))
    pix.save(str(out))
    return f'../assets/images/ref/p{pno:02d}.png'


def fill_slide(slide: dict, lines: list, image: str):
    """按模板类型回填一个 slide"""
    tpl = slide['template']
    d = slide['data']

    if tpl == 'split-image-text':
        if lines and not (d.get('cards') and d['cards'][0].get('text')):
            text = '<br>'.join(lines)
            if d.get('cards'):
                d['cards'][0]['text'] = text
            else:
                d['cards'] = [{'title': '设计说明', 'text': text}]
        if image and not d.get('image'):
            d['image'] = image

    elif tpl == 'multi-card-row':
        if image:
            for pc in d.get('photo_cards', []):
                pc['image'] = image
                break
        if lines:
            for dc in d.get('data_cards', []):
                if not dc.get('items'):
                    dc['items'] = lines[:6]
                break

    elif tpl == 'quadrant-2x2':
        if lines:
            qs = d.get('quadrants', [])
            if qs:
                chunk = (len(lines) + len(qs) - 1) // len(qs)
                for i, q in enumerate(qs):
                    if not q.get('points'):
                        q['points'] = lines[i * chunk:(i + 1) * chunk]

    elif tpl == 'scheme-present':
        # SCHEME 打架修复: 图纸页残留页码数字,必须清空
        if d.get('scheme_num') and d['scheme_num'].isdigit():
            d['scheme_num'] = ''
        if lines and not d.get('description'):
            d['description'] = '<br>'.join(lines[:6])
        if image and not d.get('image'):
            d['image'] = image


def fix_p25(d: dict):
    """slide_25 指标修正 — 仅当检测到已知错值(建筑密度 51.0%)时应用,项目无关"""
    rows = d.get('rows', [])
    if not any(r.get('b') == '51.0%' for r in rows):
        return  # 无错值(其他项目或已修正),跳过
    fixed = [
        ('用地面积', '20996.28 ㎡', '使用已有批文土地'),
        ('总建筑面积', '12243.36 ㎡', ''),
        ('地上总建筑面积', '11020.05 ㎡', ''),
        ('地上计容建筑面积', '21497.32 ㎡', '1#厂房生产区双倍计容'),
        ('地下建筑面积', '1223.31 ㎡', '地下设备用房'),
        ('容积率', '1.02', ''),
        ('建筑基底', '10784.56 ㎡', ''),
        ('建筑密度', '51.36%', ''),
        ('行政办公及生活服务区面积', '470.98 ㎡', '占比 3.85%'),
        ('车位', '42 辆', ''),
        ('非机动停车区', '98 ㎡', ''),
    ]
    d['rows'] = [
        {'indicator': ind, 'a': '', 'b': val, 'b_better': True, 'note': note}
        for ind, val, note in fixed
    ]


def main():
    global PROJECT_NAME
    ref_pdf = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(r'E:\TRAE\l-柠檬冷链物流\20260920合--安岳县柠檬冷链共享仓建设项目v2.pdf'))

    # 备份
    bak = DECK_PATH.with_suffix('.yaml.pre_ref.bak')
    if bak.exists():
        # 重跑: 从备份恢复,保证幂等
        shutil.copy2(bak, DECK_PATH)
        print(f'[恢复] 从 {bak.name} 重跑')
    else:
        shutil.copy2(DECK_PATH, bak)
        print(f'[备份] {bak.name}')

    deck = yaml.safe_load(DECK_PATH.read_text(encoding='utf-8'))
    PROJECT_NAME = deck.get('project', {}).get('name', '')
    doc = fitz.open(ref_pdf)

    filled, img_cnt = 0, 0
    for slide in deck['slides']:
        m = re.match(r'slide_(\d+)', slide['id'])
        pno = int(m.group(1))
        if pno > len(doc):
            continue

        # p25 指标修正
        if slide['id'] == 'slide_25':
            fix_p25(slide['data'])
            filled += 1
            print(f'  ✓ {slide["id"]} 指标修正(建筑密度51.36%等)')
            continue

        tpl = slide['template']
        if tpl in ('cover', 'toc', 'chapter-divider', 'closing', 'intent-bigtext'):
            continue

        page = doc[pno - 1]
        lines = clean_lines(page, slide.get('title', ''))
        image = extract_largest_image(doc, page, pno)
        before = str(slide['data'])
        fill_slide(slide, lines, image)
        if str(slide['data']) != before:
            filled += 1
        if image:
            img_cnt += 1
        print(f'  ✓ {slide["id"]} [{tpl}] lines={len(lines)} img={"Y" if image else "-"}')

    DECK_PATH.write_text(
        yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
        encoding='utf-8')
    print(f'\n[OK] 回填 {filled} 页, 接入 ref 图 {img_cnt} 张 → {REF_DIR.name}/')


if __name__ == '__main__':
    main()
