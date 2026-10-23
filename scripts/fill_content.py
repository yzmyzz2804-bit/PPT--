"""
fill_content.py - 按版式自动填充各页内容字段 (方案1: 版式即结构)

规则:
  - 每章的内容点(来自 COZE MD 章节拆解)按顺序均分给该章的内容页
  - 每种模板有固定的字段结构,内容点按 "标题：描述" 拆成 键/值
  - 只填缺失字段(setdefault),不覆盖已有数据; locked 页跳过
  - 图片一律留占位(模板显示"配图区"),同事放 assets/images/ 后在 deck.yaml 填路径

使用:
    python fill_content.py            # 填充并写回 deck.yaml
    python fill_content.py --dry      # 只预览分配,不写回
"""
import re
import sys
import argparse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'


def split_kv(item: str):
    """"道路等级：14m" → ('道路等级', '14m'); 无冒号 → (前14字, 原文)"""
    for sep in ('：', ':'):
        if sep in item:
            k, v = item.split(sep, 1)
            return k.strip(), v.strip()
    return item[:14], item


def chunk(lst, n):
    """均分成 n 组"""
    if not lst:
        return [[] for _ in range(n)]
    size = max(1, -(-len(lst) // n))
    out = [lst[i:i + size] for i in range(0, len(lst), size)]
    while len(out) < n:
        out.append([])
    return out[:n]


def get_chapter_contents(deck) -> dict:
    """{章节名: [内容点...]} 从 concept.chapters 还原"""
    out = {}
    for c in deck.get('concept', {}).get('chapters', []):
        name = c.get('word', '')
        content = c.get('content', '')
        pts = [p for p in re.split(r'[、;；]', content) if p] if content else []
        if name:
            out[name] = pts
    return out


# ---------- 各模板的填充函数 (slide, points, chinfo) ----------

def f_toc(s, pts, ch, deck):
    if s['data'].get('chapters'):
        return
    chs = deck.get('narrative_chapters', [])
    slides = deck.get('slides', [])
    # 每章页码范围: 找各 divider 位置分段
    items = []
    start = 3  # 封面+目录后
    for i, c in enumerate(chs):
        # 该章内容页数
        n = sum(1 for x in slides if x.get('chapter') == c['id'])
        items.append({
            'num': str(i + 1).zfill(2),
            'name': c['name'],
            'name_en': c.get('name_en', ''),
            'pages': f'P{start:02d} - P{start + n:02d}',
        })
        start += n + 1
    s['data']['chapters'] = items


def f_split_image_text(s, pts, ch, deck):
    d = s['data']
    cards = d.get('cards') or []
    if not cards and pts:
        cards = []
        for p in pts[:3]:
            k, v = split_kv(p)
            cards.append({'title': k, 'text': v})
    d['cards'] = cards
    d.setdefault('image', '')  # 留空 → 模板显示配图区


def f_quadrant(s, pts, ch, deck):
    d = s['data']
    d.setdefault('intro', ch.get('problem', '') or (pts[0] if pts else ''))
    groups = chunk([p for p in pts[1:] if p != pts[0]] or pts, 4)
    quads = d.get('quadrants') or []
    if not quads:
        quads = []
        for i, g in enumerate(groups):
            title = split_kv(g[0])[0] if g else f'要点 {i+1}'
            quads.append({'title': title, 'points': g})
    d['quadrants'] = quads


def f_multi_card_row(s, pts, ch, deck):
    d = s['data']
    if not d.get('data_cards') and pts:
        dcs = []
        for p in pts[:3]:
            k, v = split_kv(p)
            dcs.append({'number': v[:6], 'unit': '', 'label': k, 'items': []})
        d['data_cards'] = dcs
    if not d.get('photo_cards'):
        d['photo_cards'] = [
            {'image': '', 'title': k, 'tag': ''}
            for k, _ in [split_kv(p) for p in pts[3:6]]
        ] or [{'image': '', 'title': '配图位', 'tag': ''}]


def f_scheme_present(s, pts, ch, deck):
    d = s['data']
    m = re.search(r'(?:方案|SCHEME)\s*([0-9一二三]+)', s.get('title', '') + d.get('title', ''), re.I)
    d.setdefault('scheme_num', m.group(1) if m else '01')
    d.setdefault('scheme_name', re.sub(r'^(?:方案|SCHEME)\s*[0-9一二三]+[:：\s]*', '', s.get('title', '')))
    d.setdefault('scheme_name_en', f"SCHEME {d.get('scheme_num', '01')}")
    if not d.get('description') and pts:
        d['description'] = '；'.join(pts[:3])
    if not d.get('metrics') and pts:
        d['metrics'] = [{'key': k, 'val': v} for k, v in (split_kv(p) for p in pts[3:7])]
    d.setdefault('image', '')


def f_timeline(s, pts, ch, deck):
    d = s['data']
    if not d.get('milestones') and pts:
        ms = []
        for i, p in enumerate(pts[:6], 1):
            k, v = split_kv(p)
            ym = re.search(r'(19|20)\d{2}', p)
            ms.append({'year': ym.group(0) if ym else f'{i:02d}', 'name': k, 'desc': v})
        d['milestones'] = ms


def f_tech_stack(s, pts, ch, deck):
    d = s['data']
    if not d.get('layers') and pts:
        d['layers'] = [{'name': split_kv(p)[0], 'name_en': '', 'items': [split_kv(p)[1]]} for p in pts[:5]]


def f_flow(s, pts, ch, deck):
    d = s['data']
    if not d.get('stages') and pts:
        d['stages'] = [{'name': split_kv(p)[0], 'name_en': f'STEP {i+1}', 'desc': split_kv(p)[1]}
                       for i, p in enumerate(pts[:5])]


def f_data_chart(s, pts, ch, deck):
    d = s['data']
    d.setdefault('chart_type', 'bar')
    if not d.get('insight') and pts:
        d['insight'] = pts[0]
    if not d.get('legend') and len(pts) > 1:
        colors = ['#2562EB', '#D9822B', '#049569', '#93C4FD']
        d['legend'] = [{'label': split_kv(p)[0], 'color': colors[i % 4]} for i, p in enumerate(pts[1:5])]


def f_generic(s, pts, ch, deck):
    d = s['data']
    if pts and not d.get('points'):
        d['points'] = pts
    if pts and not d.get('subtitle'):
        d['subtitle'] = split_kv(pts[0])[0]


FILLERS = {
    'toc': f_toc,
    'split-image-text': f_split_image_text,
    'quadrant-2x2': f_quadrant,
    'multi-card-row': f_multi_card_row,
    'scheme-present': f_scheme_present,
    'analysis-timeline': f_timeline,
    'analysis-tech-stack': f_tech_stack,
    'analysis-flow': f_flow,
    'analysis-data-chart': f_data_chart,
}
SKIP = {'cover', 'chapter-divider', 'closing', 'scheme-compare', 'intent-bigtext',
        'intent-quote', 'intent-three-claim', 'intent-data-emphasis'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    args = ap.parse_args()

    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    ch_contents = get_chapter_contents(deck)
    chapters_meta = {c.get('word', ''): c for c in deck.get('concept', {}).get('chapters', [])}

    # 0. 章节重链接: 过渡页按名称匹配章节,内容页继承最近过渡页的章节
    chs = deck.get('narrative_chapters', [])
    name2id = {c['name']: c['id'] for c in chs}
    cur = ''
    for s in deck.get('slides', []):
        tpl = s.get('template', '')
        if tpl == 'chapter-divider':
            t = re.sub(r'^[0-9\s]+', '', s.get('title', ''))
            cur = name2id.get(t) or (f'ch{int(m.group(1))}' if (m := re.search(r'(\d+)', s.get('title', ''))) else '') or cur
            s['chapter'] = cur
        elif tpl in ('cover', 'toc', 'closing', 'scheme-compare') or tpl.startswith('intent'):
            continue  # 不动
        else:
            if cur:
                s['chapter'] = cur

    # 1. 按章分组,内容点均分给该章内容页
    by_ch = {}
    for s in deck.get('slides', []):
        by_ch.setdefault(s.get('chapter', ''), []).append(s)

    filled = 0
    for s in deck.get('slides', []):
        if s.get('status') == 'locked':
            continue
        tpl = s.get('template', '')
        if tpl in SKIP:
            continue
        ch_name = s.get('data', {}).get('subtitle', '')
        # 找章节: 内容页的 chapter 字段 → narrative_chapters name
        cid = s.get('chapter', '')
        cname = next((c['name'] for c in deck.get('narrative_chapters', []) if c['id'] == cid), '')
        pts_all = ch_contents.get(cname, [])
        # 章内内容页序号 → 取对应切片
        siblings = [x for x in by_ch.get(cid, []) if x.get('template', '') not in
                    ('chapter-divider',) and x.get('template', '') not in SKIP]
        idx = siblings.index(s) if s in siblings else 0
        slices = chunk(pts_all, len(siblings)) if siblings else []
        pts = slices[idx] if idx < len(slices) else []
        chinfo = {'problem': chapters_meta.get(cname, {}).get('problem', '')}

        fn = FILLERS.get(tpl, f_generic)
        before = yaml.dump(s.get('data', {}), allow_unicode=True)
        fn(s, pts, chinfo, deck)
        after = yaml.dump(s.get('data', {}), allow_unicode=True)
        if before != after:
            filled += 1
            if not args.dry:
                print(f"  ✓ {s['id']} [{tpl}] ← {len(pts)} 内容点")
            else:
                print(f"  ○ {s['id']} [{tpl}] 将填入 {len(pts)} 内容点")

    if args.dry:
        print(f'(dry) 将更新 {filled} 页')
        return

    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f'✓ 已填充 {filled} 页 → deck.yaml')


if __name__ == '__main__':
    main()
