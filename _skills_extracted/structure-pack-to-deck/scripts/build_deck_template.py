# -*- coding: utf-8 -*-
"""
build_deck_template.py — 结构包(layout-protocol v1.1) → deck.yaml 转换器参考实现

用法: 复制到新项目根目录 <项目>/build_deck.py，按标 TODO 处适配本项目后运行。
前提: source/结构定义_vX.X.json (逐页内容内嵌 slides_structure)、assets/ 已落位。

依赖: pip install pyyaml
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC_JSON = ROOT / 'source' / '结构定义_v2.4.json'   # TODO: 改为实际版本
OUT = ROOT / 'deck.yaml'

# TODO: divider 页号 → 变体 (a=带图标准 / b=超大数字 / c=摘要)
DIVIDER_VARIANTS = {}
# TODO: divider-c 页号 → points (从本章内容提炼 4 条 {num,title,desc})
DIVIDER_POINTS = {}


def asset_path(p: str) -> str:
    """协议 assets 相对路径 → slides 视角 ../assets/...；空值原样返回"""
    if not p:
        return ''
    return f'../assets/{p}' if not p.startswith('..') else p


def chapter_id(ch_str: str) -> str:
    """"01 项目背景" → ch1；空返回 ''"""
    if not ch_str:
        return ''
    m = re.match(r'\s*(\d+)', str(ch_str))
    return f'ch{int(m.group(1))}' if m else ''


def chapter_map(chapters: list) -> dict:
    """chapters[{num,pages:'P1 - P8'}] → {页码: 'chN'}"""
    out = {}
    for c in chapters:
        m = re.match(r'\s*(\d+)', c.get('num', ''))
        if not m:
            continue
        ch = f'ch{int(m.group(1))}'
        pm = re.search(r'P(\d+)\s*-\s*P(\d+)', c.get('pages', ''))
        if pm:
            for p in range(int(pm.group(1)), int(pm.group(2)) + 1):
                out[p] = ch
    return out


def convert(proto_page: dict, ch: str, page: int, total: int) -> dict:
    """协议页数据 → deck.yaml slide 条目"""
    t = proto_page['type']
    template = {
        'cover': 'cover',
        'closing': 'closing',
        'image-text-split': 'split-image-text',
        'three-cards': 'multi-card-row',
        'data-profile': 'multi-card-row',
        'comparison-table': 'compare-table',
        'chapter-divider': DIVIDER_VARIANTS.get(page, 'chapter-divider-a'),
}[t]
    d = {'page': page, 'chapter': ch, 'template': template}

    if t == 'cover':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('subtitle', '')
        d['meta'] = proto_page.get('meta', [])
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))

    elif t == 'closing':
        d['thanks_title'] = proto_page.get('thanks_title', '谢谢聆听')
        d['thanks_subtitle'] = proto_page.get('thanks_subtitle', '')
        d['concept_recap'] = proto_page.get('concept_recap', [])
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))

    elif t == 'chapter-divider':
        d['chapter_num'] = proto_page.get('chapter_num', '')
        d['chapter_title'] = proto_page.get('chapter_title', '')
        d['chapter_desc'] = proto_page.get('chapter_desc', '')
        d['chapter_concept'] = proto_page.get('chapter_concept', '')
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))
        if template == 'chapter-divider-c':
            d['points'] = DIVIDER_POINTS[page]

    elif t == 'image-text-split':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['image'] = asset_path(proto_page.get('asset', {}).get('main_image', ''))
        d['image_caption'] = proto_page.get('asset', {}).get('caption', '')
        if proto_page.get('bullets'):
            d['bullets'] = [{'icon': '', 'title': '', 'text': '<br>'.join(
                b if isinstance(b, str) else b.get('text', '')
                for b in proto_page['bullets'])}]
        else:
            d['bullets'] = []
        km = proto_page.get('key_metrics', []) or []
        d['key_metrics'] = [{'number': str(x.get('value', '')), 'unit': x.get('unit', ''),
                             'label': x.get('label', '')} for x in km]
        co = proto_page.get('callout', {}) or {}
        d['callout'] = {'text': co.get('text', ''), 'label': co.get('label', '')}

    elif t in ('three-cards', 'data-profile'):
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['tag'] = ''
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))
        src_cards = proto_page.get('cards', []) or proto_page.get('dimensions', []) or []
        if t == 'three-cards':
            d['data_cards'] = [{
                'number': '', 'unit': '',  # 纯文字卡: number/unit 留空自动隐藏
                'label': x.get('title', ''),
                'items': [{'key': '', 'val': x.get('desc', '')}],
            } for x in src_cards]
            d['photo_cards'] = []
        else:  # data-profile: value/unit 放数字位
            d['data_cards'] = [{
                'number': str(x.get('value', '')), 'unit': x.get('unit', ''),
                'label': x.get('label') or x.get('category', ''),
                'items': [{'key': '', 'val': x['desc']}] if x.get('desc') else [],
            } for x in src_cards]
            main_img = asset_path(proto_page.get('asset', {}).get('main_image', ''))
            d['photo_cards'] = ([{'image': main_img, 'title': '规划设计条件', 'tag': ''}]
                                if main_img else [])

    elif t == 'comparison-table':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['tag'] = ''
        tab = proto_page.get('table', {}) or {}
        headers = list(tab.get('headers', []))
        raw_rows = tab.get('rows', []) or []
        if len(headers) >= 4 and headers[1] == '原规划':
            # 对比语义 4 列 → 热列+备注列
            d['headers'] = [headers[0], headers[2], f'{headers[1]} / {headers[3]}']
            rows = []
            for r in raw_rows:
                old, new, chg = r[1], r[2], (r[3] if len(r) > 3 else '')
                note = old if chg in ('', '—', '-') else f'{old}（{chg}）'
                rows.append({'indicator': r[0], 'b': new, 'b_better': True, 'note': note})
        elif len(headers) >= 4:
            # 通用 4 列 → 前两列保留, 3/4 列合并进备注
            d['headers'] = [headers[0], headers[1], f'{headers[2]} / {headers[3]}']
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '', 'b_better': True,
                     'note': '<br>'.join(x for x in (r[2] if len(r) > 2 else '',
                                                     r[3] if len(r) > 3 else '') if x)}
                    for r in raw_rows]
        else:
            d['headers'] = headers[:3]
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '', 'b_better': True,
                     'note': r[2] if len(r) > 2 else ''} for r in raw_rows]
        d['rows'] = rows
        v = tab.get('verdict', {}) or proto_page.get('verdict', {}) or {}
        d['summary_cards'] = [{'name': v.get('title', '结论'), 'hot': True,
                               'items': [{'k': '', 'v': v.get('text', '')}]}]

    d['page_number'] = f'{page:02d} / {total:02d}'
    return d


def main():
    struct = json.loads(SRC_JSON.read_text(encoding='utf-8'))
    proj = struct['project']
    total = struct['total_pages']
    ch_of = chapter_map(struct.get('chapters', []))
    proto_pages = {s['page']: s for s in struct['slides_structure']}

    missing = [n for n in range(1, total + 1) if n not in proto_pages]
    if missing:
        raise SystemExit(f'结构包缺页数据: {missing}')

    slides = []
    for s in struct['slides_structure']:
        page = s['page']
        ch = chapter_id(s.get('chapter', '')) or ch_of.get(page, '')
        slides.append(convert(proto_pages[page], ch, page, total))

    deck = {
        'theme': 'blue-grey-coze',   # TODO: 按项目选择主题
        'project': {
            'name': proj.get('name', ''),
            'name_en': proj.get('name_en', ''),
            'type': proj.get('type', ''),
            'date': proj.get('date', ''),
        },
        'pages': total,
        'slides': slides,
    }
    OUT.write_text(yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
                   encoding='utf-8')
    from collections import Counter
    print(f'✓ deck.yaml 已生成: {OUT}')
    print(f'  共 {total} 页; 模板分布: {dict(Counter(s["template"] for s in slides))}')
    print(f'  章节: {sorted(set(s["chapter"] for s in slides))}')


if __name__ == '__main__':
    main()
