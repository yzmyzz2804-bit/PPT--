# -*- coding: utf-8 -*-
"""
build_deck.py — 安岳运动中心 v6 结构包(layout-protocol v1.1) → deck.yaml

一次性转换器。源: source/结构定义_v6.json（12 页 / 6 章 / 无目录 / 无分隔页）。
输出: deck.yaml，slide 条目为 {id, chapter, template, data}。
"""
import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC_JSON = ROOT / 'source' / '结构定义_v6.json'
OUT = ROOT / 'deck.yaml'

TYPE_MAP = {
    'cover': 'cover',
    'closing': 'closing',
    'image-text-split': 'split-image-text',
    'three-cards': 'multi-card-row',
    'data-profile': 'multi-card-row',
    'comparison-table': 'compare-table',
    'full-text': 'full-text',
}


def asset_path(p: str) -> str:
    """协议 assets 相对路径 → slides 视角 ../assets/...；空值原样返回"""
    if not p:
        return ''
    return p if p.startswith('..') else f'../assets/{p}'


def chapter_map(chapters: list) -> dict:
    """chapters[{num,pages:'P1 - P2'}] → {页码: ('chN', 'Concept')}"""
    out = {}
    for c in chapters:
        m = re.match(r'\s*(\d+)', c.get('num', ''))
        if not m:
            continue
        ch = f'ch{int(m.group(1))}'
        concept = c.get('concept', '')
        pages = c.get('pages', '')
        pm = re.search(r'P(\d+)\s*-\s*P(\d+)', pages)
        if pm:
            rng = range(int(pm.group(1)), int(pm.group(2)) + 1)
        else:
            sm = re.search(r'P(\d+)', pages)
            rng = [int(sm.group(1))] if sm else []
        for p in rng:
            out[p] = (ch, concept)
    return out


def split_label(text: str):
    """『【标签】正文』→ (label, text)；无标签返回 ('', text)"""
    m = re.match(r'^\s*【(.+?)】\s*(.*)$', text or '')
    return (m.group(1), m.group(2)) if m else ('', text or '')


def convert(proto: dict, ch: str, concept: str, page: int, total: int) -> dict:
    t = proto['type']
    template = TYPE_MAP[t]
    d = {}
    tag = concept.upper()

    if t == 'cover':
        sub = proto.get('subtitle', '')
        meta = proto.get('meta', {}) or {}
        if meta.get('tagline'):
            sub = f'{sub}　·　{meta["tagline"]}'
        d['title'] = proto.get('title', '')
        d['subtitle'] = sub
        d['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))

    elif t == 'closing':
        d['closing_text'] = f'{proto.get("thanks_title", "谢谢聆听")} · ' \
                            f'{proto.get("thanks_subtitle", "")}'.rstrip(' ·')
        d['closing_sub'] = proto.get('concept_recap', '')
        d['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))

    elif t == 'data-profile':
        d['tag'] = tag
        d['title'] = proto.get('title', '')
        d['subtitle'] = proto.get('title_en', '')
        d['data_cards'] = [{
            'number': str(km.get('value', '')),
            'unit': km.get('unit', ''),
            'label': km.get('label', ''),
            'items': [{'key': '', 'val': km['note']}] if km.get('note') else [],
        } for km in proto.get('key_metrics', [])]
        d['photo_cards'] = []
        d['footnote'] = proto.get('conclusion', '')

    elif t == 'image-text-split':
        content = proto.get('content', {}) or {}
        d['tag'] = tag
        d['title'] = proto.get('title', '')
        d['subtitle'] = proto.get('title_en', '')
        d['image'] = asset_path(proto.get('asset', {}).get('main_image', ''))
        d['image_second'] = asset_path(proto.get('asset', {}).get('second_image', ''))
        cards = []
        if content.get('sections'):
            if content.get('callout'):
                cards.append({'title': '核心逻辑', 'text': content['callout']})
            for s in content['sections']:
                cards.append({'title': s.get('label', ''),
                              'text': '<br>'.join(s.get('items', []))})
        elif content.get('bullets'):
            cards.append({'title': content.get('callout', ''),
                          'text': '<br>'.join(content['bullets'])})
        d['cards'] = cards

    elif t == 'three-cards':
        d['tag'] = tag
        d['title'] = proto.get('title', '')
        d['subtitle'] = proto.get('title_en', '')
        d['data_cards'] = [{
            'number': c.get('title', ''),                       # 主词: 石隐 / 功能转换
            'unit': c.get('role') or c.get('path') or c.get('no', ''),  # 眉标: 文化·形 / 形·藏 / 机制 01
            'label': c.get('title_en') or c.get('subtitle', ''),        # 次词
            'items': [{'key': '', 'val': c.get('desc', '')}],
        } for c in proto.get('cards', [])]
        d['photo_cards'] = []
        d['footnote'] = proto.get('bottom_statement', '')

    elif t == 'comparison-table':
        d['tag'] = tag
        d['title'] = proto.get('title', '')
        d['subtitle'] = proto.get('title_en', '')
        tab = proto.get('table', {}) or {}
        headers = list(tab.get('headers', []))
        raw = tab.get('rows', []) or []
        case_images = []
        asset = proto.get('asset', {}) or {}
        if asset.get('left_image'):
            case_images.append({'image': asset_path(asset['left_image']),
                                'caption': headers[1] if len(headers) > 1 else ''})
        if asset.get('right_image'):
            case_images.append({'image': asset_path(asset['right_image']),
                                'caption': headers[2] if len(headers) > 2 else ''})
        d['case_images'] = case_images

        if len(headers) >= 5:
            # 5 列(功能/层级/内容/配比/面积) → 压缩为 3 列
            d['headers'] = [f'{headers[0]} · {headers[1]}', headers[2],
                            f'{headers[3]} · {headers[4]}']
            rows = [{
                'indicator': f'{r[0]} · {r[1]}',
                'b': r[2] if len(r) > 2 else '',
                'b_better': False,
                'note': f'{r[3]} · {r[4]}' if len(r) > 4 else '',
            } for r in raw]
            note = proto.get('note', '')
            d['summary_cards'] = ([{'name': '落点', 'hot': True,
                                    'items': [{'k': '', 'v': note}]}] if note else [])
        else:
            d['headers'] = headers[:3]
            rows = [{
                'indicator': r[0],
                'b': r[1] if len(r) > 1 else '',
                'b_better': True,       # 热列=嘉兴(自我造血范式)
                'note': r[2] if len(r) > 2 else '',
            } for r in raw]
            v = proto.get('verdict', {}) or {}
            d['summary_cards'] = [{'name': v.get('label', '落点'), 'hot': True,
                                   'items': [{'k': '', 'v': v.get('text', '')}]}]
        d['rows'] = rows

    elif t == 'full-text':
        content = proto.get('content', {}) or {}
        d['tag'] = tag
        d['title'] = proto.get('title', '') or _chapter_title(proto, ch)
        d['subtitle'] = proto.get('title_en', '')
        d['formula'] = proto.get('formula', '')
        d['paragraphs'] = [dict(zip(('label', 'text'), split_label(p)))
                           for p in content.get('paragraphs', [])]

    return {'id': f'slide_{page:02d}', 'chapter': ch, 'template': template, 'data': d}


def _chapter_title(proto: dict, ch: str) -> str:
    """full-text 页缺 title 时，用本章标题兜底"""
    return CHAPTER_TITLES.get(ch, '')


CHAPTER_TITLES = {}


def main():
    struct = json.loads(SRC_JSON.read_text(encoding='utf-8'))
    proj = struct['project']
    total = struct['total_pages']
    ch_of = chapter_map(struct.get('chapters', []))

    global CHAPTER_TITLES
    CHAPTER_TITLES = {f'ch{int(re.match(r"(\d+)", c["num"]).group(1))}': c.get('title', '')
                      for c in struct.get('chapters', []) if re.match(r'\s*(\d+)', c.get('num', ''))}

    slides = []
    for s in struct['slides_structure']:
        page = s['page']
        ch, concept = ch_of.get(page, ('', ''))
        slides.append(convert(s, ch, concept, page, total))

    loc = proj.get('location', '')
    deck = {
        'theme': proj.get('theme', 'light-health'),
        'project': {
            'name': proj.get('name', ''),
            'name_en': proj.get('name_en', ''),
            'type': proj.get('type', ''),
            'date': f'{proj.get("date", "")} · {loc}'.rstrip(' ·'),
        },
        'pages': total,
        'slides': slides,
    }
    OUT.write_text(yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
                   encoding='utf-8')
    print(f'✓ deck.yaml 已生成: {OUT}')
    print(f'  共 {total} 页; 模板分布: {dict(Counter(s["template"] for s in slides))}')
    print(f'  章节: {sorted({s["chapter"] for s in slides})}')


if __name__ == '__main__':
    main()
