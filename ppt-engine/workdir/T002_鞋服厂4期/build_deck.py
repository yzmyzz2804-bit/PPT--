# -*- coding: utf-8 -*-
"""
build_deck.py — T002 安岳鞋服厂4期 结构定义 v4.0 → deck.yaml (v4)
v4 变更（方案内容调整）：
- 核心主张 →「独立成园 · 共享配套」；两方向=不配宿舍 / 园区集中配宿舍
- 场地中央留公共进入空间，各园独立入口昭示，大园区统一配套与水电管理
- 指标口径沿用 0921 三方案，8 行数值零改动
- 概念主旨/设计愿景/方案呈现/指标四章同步改写
"""
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
SRC_JSON = ROOT / 'source' / '结构定义_v6.0.json'
OUT = ROOT / 'deck.yaml'

P8_CAPTIONS = ['南京天印智造谷 · gooood', '东莞迪桑娜皮具工业园 · gooood']
DIVIDER_BG = '../assets/images/site/site_aerial.jpg'

# 分隔页定义：章号 → (章名, 英文, 描述)
DIVIDERS = {
    1: ('场地研判', 'Site Analysis',
        '读懂场地——区位、用地与交通条件，是方案生成的起点'),
    2: ('产业洞察', 'Industry Insight',
        '从企业规模、验厂规则到智能产线，锁定厂房产品的真实需求'),
    3: ('概念主旨', 'Concept',
        '独立成园 · 共享配套——回应企业独立园区与业主资源统筹的双重诉求'),
    4: ('案例佐证', 'Case Proof',
        '同体量产业园的成熟做法，印证概念的可实现性'),
    5: ('设计愿景', 'Vision & Landing',
        '独立成园、共享配套、梯度生长，各落一组可执行的规划动作'),
    6: ('方案呈现', 'Schemes',
        '不配宿舍与园区集中配宿舍两方向比选：快启快租，或全规模覆盖'),
    7: ('指标与技术分析', 'Metrics & Technique',
        '合规底线之上的策略取舍，与间距、退界、流线校核'),
}


def ap(p: str) -> str:
    return f'../assets/{p}' if p else ''


def callout_card(callout: str) -> dict:
    return {'title': callout, 'text': ''}


def sections_cards(content: dict) -> list:
    cards = []
    co = content.get('callout', '')
    if co:
        cards.append(callout_card(co))
    for sec in content.get('sections', []):
        items = sec.get('items', [])
        text = '<br>'.join('· ' + i for i in items)
        cards.append({'title': sec.get('label', ''), 'text': text})
    return cards


def bullets_card(content: dict) -> list:
    co = content.get('callout', '')
    bl = content.get('bullets', [])
    return [{'title': co, 'text': '<br>'.join('· ' + b for b in bl)}]


def convert(s: dict, ch: str, page: int) -> dict:
    t = s['type']
    asset = s.get('asset', {}) or {}
    d = {}

    if t == 'cover':
        meta = s.get('meta', {}) or {}
        d['template'] = 'cover-soft'
        d['title'] = s.get('title', '')
        d['subtitle'] = s.get('subtitle', '') + '<br>' + meta.get('tagline', '')
        d['date'] = f"{meta.get('location', '')} · {s_date}"
        d['bg_image'] = ap(asset.get('bg_image', ''))

    elif t == 'toc':
        d['template'] = 'toc'
        # 2026-10-16 规则：目录不再标注页码范围，仅保留章号/章名/英文
        d['chapters'] = [{'num': c['num'], 'name': c['title'],
                          'name_en': c.get('concept', '')}
                         for c in s.get('chapters', [])]

    elif t == 'closing':
        d['template'] = 'closing'
        d['closing_text'] = s.get('thanks_title', '')
        d['closing_sub'] = s.get('thanks_subtitle', '') + '<br>' + s.get('concept_recap', '')
        d['bg_image'] = ap(asset.get('bg_image', ''))

    elif t == 'image-text-split':
        d['template'] = 'split-image-text'
        d['title'] = s.get('title', '')
        d['subtitle'] = s.get('title_en', '')
        d['tag'] = s.get('chapter_label', '')
        d['image'] = ap(asset.get('main_image', ''))
        d['image_second'] = ap(asset.get('second_image', ''))
        d['reverse'] = (s.get('layout', {}).get('image_position') == 'right')
        content = s.get('content', {}) or {}
        d['cards'] = sections_cards(content) if content.get('sections') else bullets_card(content)

    elif t in ('three-cards', 'data-profile'):
        d['template'] = 'multi-card-row'
        d['title'] = s.get('title', '')
        d['subtitle'] = s.get('title_en', '')
        d['tag'] = s.get('chapter_label', '')
        if t == 'three-cards':
            d['data_cards'] = [{'number': '', 'unit': '',
                                'label': c.get('title', ''),
                                'items': [{'key': c.get('role') or c.get('path', ''),
                                           'val': c.get('desc', '')}]}
                               for c in s.get('cards', [])]
        else:
            d['data_cards'] = [{'number': str(k.get('value', '')), 'unit': '',
                                'label': k.get('label', ''),
                                'items': [{'key': '', 'val': k.get('note', '')}]}
                               for k in s.get('key_metrics', [])]
        d['photo_cards'] = []
        d['footnote'] = s.get('bottom_statement', '') or s.get('conclusion', '')

    elif t == 'comparison-table':
        d['template'] = 'compare-table'
        d['title'] = s.get('title', '')
        d['subtitle'] = s.get('title_en', '')
        d['tag'] = s.get('chapter_label', '')
        tab = s.get('table', {}) or {}
        d['headers'] = tab.get('headers', [])[:3]
        d['rows'] = [{'indicator': r[0],
                      'b': r[1] if len(r) > 1 else '',
                      'b_better': False,
                      'note': r[2] if len(r) > 2 else ''}
                     for r in tab.get('rows', [])]
        if s.get('page') == 8:
            imgs = [('images/cases/case_a2.jpg', P8_CAPTIONS[0]),
                    ('images/cases/case_b2.jpg', P8_CAPTIONS[1])]
            d['case_images'] = [{'image': ap(p), 'caption': c} for p, c in imgs]
        else:
            d['case_images'] = []
        v = s.get('verdict', {}) or {}
        d['summary_cards'] = [{'name': v.get('label', '结论'), 'hot': True,
                               'items': [{'k': '', 'v': v.get('text', '')}]}]

    elif t == 'full-text':
        d['template'] = 'full-text'
        d['title'] = s.get('title', '')
        d['subtitle'] = s.get('title_en', '')
        d['tag'] = s.get('chapter_label', '')
        d['formula'] = ''
        paras = []
        for raw in s.get('content', {}).get('paragraphs', []):
            m = re.match(r'【(.+?)】(.*)', raw)
            paras.append({'label': m.group(1), 'text': m.group(2)} if m
                         else {'label': '', 'text': raw})
        d['paragraphs'] = paras

    return d


def divider_slide(num: int, page: int) -> dict:
    name, en, desc = DIVIDERS[num]
    return {
        'id': f'slide_{page:02d}',
        'chapter': f'ch{num}',
        'template': 'chapter-divider-a',
        'title': f'{num:02d} {name}',
        'status': 'pending',
        'data': {
            'chapter_num': f'{num:02d}',
            'chapter_name': name,
            'chapter_name_en': en,
            'chapter_desc': desc,
            'bg_image': DIVIDER_BG,
        },
    }


def main():
    global s_date
    struct = json.loads(SRC_JSON.read_text(encoding='utf-8'))
    proj = struct['project']
    s_date = proj.get('date', '')

    # ---- 1. 转换 16 页内容页 ----
    content_slides = []   # (原页码, slide_dict)
    for s in struct['slides_structure']:
        page = s['page']
        if page == 1:
            ch = ''
        elif page == 2:
            ch = ''
        else:
            # 原 P3-16 → ch 由章节归属: P3=ch1, P4-6=ch2, P7=ch3, P8=ch4, P9-10=ch5, P11-12=ch6, P13-14=ch7, P15-16=ch8
            ch = {3: 'ch1', 4: 'ch2', 5: 'ch2', 6: 'ch2', 7: 'ch3', 8: 'ch4',
                  9: 'ch5', 10: 'ch5', 11: 'ch6', 12: 'ch6', 13: 'ch7', 14: 'ch7',
                  15: 'ch8', 16: 'ch8'}[page]
        sd = convert(s, ch, page)
        title = sd.get('title', '') or s.get('thanks_title', '目录')
        content_slides.append({
            'id': f'slide_{page:02d}',
            'chapter': ch,
            'template': sd.pop('template'),
            'title': title,
            'status': 'pending',
            'data': sd,
        })
    by_page = {i + 1: sl for i, sl in enumerate(content_slides)}  # 原页码1-16

    # ---- 2. 章节分隔与页序（2026-10-16：目录已不再标注页码范围，故不做页码重算）----
    ch_pages = {3: 1, 4: 2, 7: 3, 8: 4, 9: 5, 11: 6, 13: 7}  # 原页码 → 其章 divider 编号

    # ---- 3. 组装 slides ----
    slides = [by_page[1], by_page[2]]
    for orig in range(3, 17):
        if orig in ch_pages:
            slides.append(divider_slide(ch_pages[orig], len(slides) + 1))
        slides.append(by_page[orig])

    # ---- 4. id 按最终页序统一重编（避免 divider 与内容页 id 冲突覆盖）----
    for i, sl in enumerate(slides, 1):
        sl['id'] = f'slide_{i:02d}'

    deck = {
        'theme': 'blue-grey-coze',
        'project': {
            'name': proj.get('name', ''),
            'name_en': proj.get('name_en', ''),
            'type': proj.get('type', ''),
            'date': proj.get('date', ''),
        },
        'pages': len(slides),
        'slides': slides,
    }
    OUT.write_text(yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
                   encoding='utf-8')
    from collections import Counter
    print(f'OK deck.yaml: {OUT}')
    print(f'  共 {len(slides)} 页; 模板分布: {dict(Counter(s["template"] for s in slides))}')
    print('  目录：不标注页码范围（2026-10-16 规则）')


if __name__ == '__main__':
    main()
