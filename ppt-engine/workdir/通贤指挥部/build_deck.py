# -*- coding: utf-8 -*-
"""
build_deck.py - 通贤指挥部结构包 → deck.yaml 转换器

本项目特定适配:
  - content 子字典: bullets/callout/key_metrics 嵌在 content{} 下
  - data_sections 分组格式: data-profile 用 {section_label, items[]} 分 3 组 12 项
  - chapter_subtitle → chapter_desc
  - 全部分隔页带 bg_image → 统一 chapter-divider-a
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC_JSON = ROOT / 'source' / '结构定义_v1.0.json'
OUT = ROOT / 'deck.yaml'

# 7 个章节页全带底图 → 统一 a 型(左 45% 底图)
DIVIDER_VARIANTS = {p: 'chapter-divider-a' for p in (2, 6, 9, 12, 17, 21, 24)}
DIVIDER_POINTS = {}


def asset_path(p: str) -> str:
    if not p:
        return ''
    return f'../assets/{p}' if not p.startswith('..') else p


def chapter_id(ch_str: str) -> str:
    if not ch_str:
        return ''
    m = re.match(r'\s*(\d+)', str(ch_str))
    return f'ch{int(m.group(1))}' if m else ''


def chapter_map(chapters: list) -> dict:
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
        else:
            pm2 = re.search(r'P(\d+)', c.get('pages', ''))
            if pm2:
                out[int(pm2.group(1))] = ch
    return out


def convert(proto: dict, ch: str, page: int, total: int) -> dict:
    t = proto['type']
    template = {
        'cover': 'cover', 'closing': 'closing',
        'image-text-split': 'split-image-text',
        'three-cards': 'multi-card-row', 'data-profile': 'multi-card-row',
        'comparison-table': 'compare-table',
        'chapter-divider': DIVIDER_VARIANTS.get(page, 'chapter-divider-a'),
    }[t]
    data = {}
    data['page_number'] = f'{page:02d} / {total:02d}'

    # content 子字典兜底: 先查 content{}, 再查顶層
    content = proto.get('content', {}) or {}

    def cget(key, default=None):
        v = content.get(key)
        if v is not None:
            return v
        return proto.get(key, default)

    if t == 'cover':
        data['title'] = proto.get('title', '')
        data['subtitle'] = proto.get('subtitle', '')
        data['meta'] = list(proto.get('meta', {}).values()) if isinstance(proto.get('meta'), dict) else (proto.get('meta') or [])
        data['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))

    elif t == 'closing':
        data['closing_text'] = proto.get('thanks_title', '谢谢聆听')
        data['closing_sub'] = proto.get('thanks_subtitle', '')
        data['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))

    elif t == 'chapter-divider':
        data['chapter_num'] = proto.get('chapter_num', '')
        data['chapter_title'] = proto.get('chapter_title', '')
        data['chapter_desc'] = proto.get('chapter_subtitle', '') or proto.get('chapter_desc', '')
        data['chapter_concept'] = proto.get('chapter_concept', '')
        data['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))
        if template == 'chapter-divider-c':
            data['points'] = DIVIDER_POINTS.get(page, [])

    elif t == 'image-text-split':
        data['title'] = proto.get('title', '')
        data['subtitle'] = proto.get('title_en', '')
        data['image'] = asset_path(proto.get('asset', {}).get('main_image', ''))
        data['image_caption'] = proto.get('asset', {}).get('caption', '')
        bullets = cget('bullets', []) or []
        data['bullets'] = [{'icon': '', 'title': '', 'text': '<br>'.join(
            b if isinstance(b, str) else b.get('text', '') for b in bullets)}] if bullets else []
        km = cget('key_metrics', []) or []
        data['key_metrics'] = [{'number': str(x.get('value', '')), 'unit': x.get('unit', ''),
                                'label': x.get('label', '')} for x in km]
        co = cget('callout', {}) or {}
        data['callout'] = {'text': co if isinstance(co, str) else co.get('text', ''),
                           'label': '' if isinstance(co, str) else co.get('label', '')}

    elif t == 'three-cards':
        data['title'] = proto.get('title', '')
        data['subtitle'] = proto.get('title_en', '')
        data['tag'] = ''
        data['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))
        cards = proto.get('cards', []) or []
        data['data_cards'] = [{
            'number': '', 'unit': '',
            'label': x.get('title', ''),
            'items': [{'key': '', 'val': x.get('desc', '')}],
        } for x in cards]
        data['photo_cards'] = []

    elif t == 'data-profile':
        data['title'] = proto.get('title', '')
        data['subtitle'] = proto.get('title_en', '')
        data['tag'] = ''
        data['bg_image'] = asset_path(proto.get('asset', {}).get('bg_image', ''))
        # data_sections 分组格式 → 摊平为 data_cards
        sections = proto.get('data_sections', []) or []
        cards = []
        for sec in sections:
            for item in sec.get('items', []):
                cards.append({
                    'number': str(item.get('value', '')),
                    'unit': item.get('unit', ''),
                    'label': item.get('label', ''),
                    'items': [],
                })
        data['data_cards'] = cards
        data['photo_cards'] = []

    elif t == 'comparison-table':
        data['title'] = proto.get('title', '')
        data['subtitle'] = proto.get('title_en', '')
        data['tag'] = ''
        tab = proto.get('table', {}) or {}
        headers = list(tab.get('headers', []))
        raw_rows = tab.get('rows', []) or []
        if len(headers) >= 4 and headers[1] == '原规划':
            data['headers'] = [headers[0], headers[2], f'{headers[1]} / {headers[3]}']
            rows = []
            for r in raw_rows:
                old, new, chg = r[1], r[2], (r[3] if len(r) > 3 else '')
                note = old if chg in ('', '—', '-') else f'{old}（{chg}）'
                rows.append({'indicator': r[0], 'b': new, 'b_better': True, 'note': note})
        elif len(headers) >= 4:
            data['headers'] = [headers[0], headers[1], f'{headers[2]} / {headers[3]}']
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '', 'b_better': True,
                     'note': '<br>'.join(x for x in (r[2] if len(r) > 2 else '',
                                                     r[3] if len(r) > 3 else '') if x)}
                    for r in raw_rows]
        else:
            data['headers'] = headers[:3]
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '', 'b_better': True,
                     'note': r[2] if len(r) > 2 else ''} for r in raw_rows]
        data['rows'] = rows
        v = tab.get('verdict', {}) or proto.get('verdict', {}) or {}
        data['summary_cards'] = [{'name': v.get('label', v.get('title', '结论')), 'hot': True,
                                  'items': [{'k': '', 'v': v.get('text', '')}]}]

    return {'id': f'slide_{page:02d}', 'chapter': ch, 'template': template, 'data': data}


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
        ch = chapter_id(s.get('chapter_num', '')) or ch_of.get(page, '')
        slides.append(convert(proto_pages[page], ch, page, total))

    deck = {
        'theme': 'blue-grey-coze',
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
