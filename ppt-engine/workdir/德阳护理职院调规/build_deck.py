# -*- coding: utf-8 -*-
"""
build_deck.py - 结构包(layout-protocol v1.1) → deck.yaml 一次性转换器

输入(v2.3 起):
  source/结构定义_v2.3.json   章节/骨架/逐页完整内容(bullets/cards/table/dimensions)
  source/内容大纲_v2.1.md     [可选] v2.1 时代的逐页 YAML 块,存在时优先
输出:
  deck.yaml                   引擎渲染管线格式

约定:
  - 素材已随 v2.3 包到位(deyang_assets → assets/),asset 路径映射 ../assets/...
  - 章节页按页号分配分隔页变体; slide.chapter 按章节页码范围推导,接分章色体系
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC_JSON = ROOT / 'source' / '结构定义_v2.4.json'
OUT = ROOT / 'deck.yaml'

# 章节页变体分配 (9 ch2愿景→b全屏数字 / 15 ch4核心→a带图 / 22 ch6意向→c摘要)
DIVIDER_VARIANTS = {9: 'chapter-divider-b', 15: 'chapter-divider-a',
                    22: 'chapter-divider-c'}

# ch6 摘要型分隔页要点 (取自 P23 建筑风格 DNA)
CH7_POINTS = [
    {'num': '01', 'title': '体量性格', 'desc': '敦厚质朴、厚重不笨重，横向舒展，立面有序韵律'},
    {'num': '02', 'title': '色彩系统', 'desc': '暖灰/米黄主基调 + 深灰勾勒轮廓 + 木色点缀室内'},
    {'num': '03', 'title': '立面母题', 'desc': '规整条窗 + 水平韵律 + 实墙与玻璃的节奏对比'},
    {'num': '04', 'title': '统一窗系统', 'desc': '全校同款窗（深灰框+等距分格），排列组合形成韵律'},
]

DIVIDER_POINTS = {22: CH7_POINTS}


def asset_path(p: str) -> str:
    """协议 assets/ 相对路径 → slides/ 视角 ../assets/..."""
    if not p:
        return ''
    if p.startswith('../') or p.startswith('/'):
        return p
    return f'../assets/{p}'


def chapter_id(ch_str: str) -> str:
    """'01 项目背景' → 'ch1'; '封面'/'结尾' → ''"""
    m = re.match(r'\s*(\d+)', ch_str or '')
    return f'ch{int(m.group(1))}' if m else ''


def convert(proto_page: dict, ch: str, page: int, total: int) -> dict:
    """协议单页 → deck.yaml slide"""
    t = proto_page['type']
    d = {}
    template = {
        'cover': 'cover',
        'closing': 'closing',
        'image-text-split': 'split-image-text',
        'three-cards': 'multi-card-row',
        'data-profile': 'multi-card-row',
        'comparison-table': 'compare-table',
        'chapter-divider': DIVIDER_VARIANTS.get(page, 'chapter-divider-a'),
    }[t]

    if t == 'cover':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('subtitle', '')
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))

    elif t == 'closing':
        subs = [proto_page.get('concept_recap', ''),
                proto_page.get('thanks_subtitle', '')]
        d['closing_text'] = proto_page.get('thanks_title', '')
        d['closing_sub'] = '<br>'.join(s for s in subs if s)
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))

    elif t == 'chapter-divider':
        d['chapter_num'] = proto_page.get('chapter_num', '')
        d['chapter_name'] = proto_page.get('chapter_title', '')
        d['chapter_name_en'] = proto_page.get('chapter_concept', '')
        d['chapter_desc'] = proto_page.get('chapter_subtitle', '')
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))
        if template == 'chapter-divider-c':
            d['points'] = DIVIDER_POINTS[page]

    elif t == 'image-text-split':
        content = proto_page.get('content', {}) or {}
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['tag'] = content.get('callout', '')
        d['image'] = asset_path(proto_page.get('asset', {}).get('main_image', ''))
        cards = []
        bullets = content.get('bullets', []) or []
        if bullets:
            cards.append({'title': '', 'text': '<br>'.join(bullets)})
        elif content.get('callout'):
            # 鸟瞰等无 bullets 页: callout 作为定位卡,避免右栏空荡
            cards.append({'title': '核心定位', 'text': content['callout']})
        metrics = content.get('key_metrics', []) or []
        if metrics:
            lines = [f'{m.get("label", "")}：{m.get("value", "")}' for m in metrics]
            cards.append({'title': '核心指标', 'text': '<br>'.join(lines)})
        d['cards'] = cards

    elif t == 'three-cards':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['tag'] = ''
        d['data_cards'] = [{
            'number': '', 'unit': '',
            'label': c.get('title', ''),
            'items': [{'key': '', 'val': c.get('desc', '')}] if c.get('desc') else [],
        } for c in (proto_page.get('cards', []) or [])]
        d['photo_cards'] = []  # 图标为字母圆环装饰,不进卡片布局,保持纯文字卡
        d['bg_image'] = asset_path(proto_page.get('asset', {}).get('bg_image', ''))

    elif t == 'data-profile':
        d['title'] = proto_page.get('title', '')
        d['subtitle'] = proto_page.get('title_en', '')
        d['tag'] = ''
        d['data_cards'] = [{
            'number': str(x.get('value', '')),
            'unit': x.get('unit', ''),
            'label': x.get('label') or x.get('category', ''),
            'items': [{'key': '', 'val': x['desc']}] if x.get('desc') else [],
        } for x in (proto_page.get('dimensions', []) or [])]
        # v2.3: data-profile 也带主图 → 单张宽幅图卡排在指标行下方
        main_img = asset_path(proto_page.get('asset', {}).get('main_image', ''))
        d['photo_cards'] = ([{'image': main_img, 'title': '规划设计条件', 'tag': ''}]
                            if main_img else [])

    elif t == 'comparison-table':
        table = proto_page.get('table', {}) or {}
        headers = table.get('headers', [])
        raw_rows = table.get('rows', [])
        if len(headers) >= 4 and headers[1] == '原规划':
            # 4 列(指标/原规划/调规后/变化)压进模板固定 3 列: 调规后为热列
            d['headers'] = [headers[0], headers[2], f'{headers[1]} / {headers[3]}']
            rows = []
            for r in raw_rows:
                old, new, chg = r[1], r[2], (r[3] if len(r) > 3 else '')
                note = old if chg in ('', '—', '-') else f'{old}（{chg}）'
                rows.append({'indicator': r[0], 'b': new, 'b_better': True,
                             'note': note})
        elif len(headers) >= 4:
            # 通用 4 列压缩: 前两列保留,第 3/4 列合并进备注列
            d['headers'] = [headers[0], headers[1], f'{headers[2]} / {headers[3]}']
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '',
                     'b_better': True,
                     'note': '<br>'.join(x for x in (r[2] if len(r) > 2 else '',
                                                     r[3] if len(r) > 3 else '') if x)}
                    for r in raw_rows]
        else:
            d['headers'] = headers[:3]
            rows = [{'indicator': r[0], 'b': r[1] if len(r) > 1 else '',
                     'b_better': True,
                     'note': r[2] if len(r) > 2 else ''} for r in raw_rows]
        d['rows'] = rows
        # MD 中 verdict 缩进在 table 下,兼容两种层级
        verdict = table.get('verdict', {}) or proto_page.get('verdict', {}) or {}
        d['summary_cards'] = [{
            'name': verdict.get('label', '结论'),
            'items': [{'k': '', 'v': verdict.get('text', '')}],
            'hot': True,
        }] if verdict else []
        d['tag'] = ''

    return {
        'id': f'slide_{page:02d}',
        'chapter': ch,
        'template': template,
        'title': proto_page.get('title', ''),
        'status': 'draft',
        'data': d,
    }


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


def main():
    struct = json.loads(SRC_JSON.read_text(encoding='utf-8'))
    proj = struct['project']
    total = struct['total_pages']
    ch_of = chapter_map(struct.get('chapters', []))

    # v2.3 起内容全部内嵌 JSON slides_structure,纯 JSON 数据源
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
        'project': {
            'name': proj.get('name', ''),
            'name_en': proj.get('name_en', ''),
            'type': proj.get('type', ''),
            'date': proj.get('date', ''),
        },
        'theme': 'blue-grey-coze',
        'slides': slides,
    }
    OUT.write_text(yaml.dump(deck, allow_unicode=True, sort_keys=False,
                             default_flow_style=False, width=4096),
                   encoding='utf-8')
    from collections import Counter
    cnt = Counter(s['template'] for s in slides)
    print(f'✓ deck.yaml 已生成: {OUT}')
    print(f'  共 {total} 页; 模板分布: {dict(cnt)}')
    print(f'  章节: {sorted(set(s["chapter"] for s in slides if s["chapter"]))}')


if __name__ == '__main__':
    main()
