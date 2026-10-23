"""
render_protocol.py - PPT Layout Protocol v1.0 适配器

将 COZE 输出的 page_protocol.json 转换为 deck.yaml 格式,
复用现有渲染管线 (render_slide.py + build_pdf.py)。

协议: 8 种版式 (cover/closing/toc/chapter-divider/image-text-split/
      three-cards/comparison-table/data-profile) + 4 种主题

使用:
    python render_protocol.py --input page_protocol.json
    python render_protocol.py --input page_protocol.json --skip-bg-gen
    python render_protocol.py --input page_protocol.json --output result.pdf

COZE 沙箱: 加 --skip-bg-gen 跳过意向图生成 (无图像 API)
"""
import sys
import json
import argparse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
SLIDES_DIR = PROJECT_ROOT / 'slides'
BUILD_DIR = PROJECT_ROOT / 'build'

# ================================================================
# 协议 → 现有模板映射
# ================================================================
TYPE_MAP = {
    'cover': 'cover',
    'closing': 'closing',
    'toc': 'toc',
    'chapter-divider': 'chapter-divider',
    'image-text-split': 'split-image-text',
    'three-cards': 'multi-card-row',
    'comparison-table': 'compare-table',
    'data-profile': 'multi-card-row',
}

# 协议主题 → 现有 theme.json (仅元数据标签,实际配色由 theme.json 决定)
THEME_MAP = {
    'blue-grey-business': 'blue-grey-coze',
    'dark-tech': 'black-white-grey',
    'warm-paper': 'ochre',
    'green-eco': 'ink-green',
}

# 协议必填字段校验表
REQUIRED_FIELDS = {
    'cover': ['title', 'subtitle'],
    'closing': ['thanks_title'],
    'toc': ['chapters'],
    'chapter-divider': ['chapter_num', 'chapter_title'],
    'image-text-split': ['title', 'content'],
    'three-cards': ['title', 'cards'],
    'comparison-table': ['title', 'table'],
    'data-profile': ['title', 'dimensions'],
}

VALID_TYPES = set(TYPE_MAP.keys())


# ================================================================
# 资产路径转换
# ================================================================
def convert_asset_path(path: str, assets_base: str) -> str:
    """协议路径 (相对 assets_base_path) → 模板路径 (相对 slides/ 目录)

    "bg/cover.jpg" + base "assets/" → "../assets/bg/cover.jpg"
    已是 ../ 开头的不转换 (兼容手填路径)
    """
    if not path:
        return ''
    if path.startswith('../') or path.startswith('/'):
        return path
    base = assets_base.rstrip('/')
    return f'../{base}/{path}' if base else f'../{path}'


# ================================================================
# 校验
# ================================================================
def validate(protocol: dict) -> list:
    """按协议 §6 校验,返回错误列表 (空=通过)"""
    errors = []
    slides = protocol.get('slides', [])
    if not slides:
        errors.append('slides 数组为空')
        return errors

    for i, s in enumerate(slides, 1):
        stype = s.get('type', '')
        if stype not in VALID_TYPES:
            errors.append(f'第{i}页: type "{stype}" 不在 8 种合法版式中')
            continue
        for fld in REQUIRED_FIELDS.get(stype, []):
            if not s.get(fld):
                errors.append(f'第{i}页 ({stype}): 缺少必填字段 "{fld}"')

    # 页码连续性
    pages = [s.get('page', 0) for s in slides]
    for i, p in enumerate(pages):
        if p == 0:
            errors.append(f'第{i+1}页: 缺少 page 字段')
        elif i > 0 and p != pages[i - 1] + 1:
            errors.append(f'第{i+1}页: 页码 {p} 与前页 {pages[i-1]} 不连续')
    return errors


# ================================================================
# 版式转换器: 协议 slide → deck.yaml slide
# ================================================================
def convert_slide(slide: dict, page_idx: int, total: int,
                  project: dict, assets_base: str) -> dict:
    """将单个协议 slide 转为 deck.yaml 格式"""
    stype = slide['type']
    template = TYPE_MAP[stype]
    sid = f'slide_{page_idx:02d}'
    data = {}
    pname = project.get('name', '')
    pname_en = project.get('name_en', '')

    # ---- 公共字段 ----
    data['project_name'] = pname
    data['project_name_en'] = pname_en
    data['page_num'] = str(page_idx)
    data['total_pages'] = str(total)

    if stype == 'cover':
        data['title'] = slide.get('title', '')
        data['subtitle'] = slide.get('subtitle', '')
        data['date'] = slide.get('meta', {}).get('date', '')
        asset = slide.get('asset', {})
        data['bg_image'] = convert_asset_path(
            asset.get('bg_image', ''), assets_base)

    elif stype == 'closing':
        data['closing_text'] = slide.get('thanks_title', '')
        recap = slide.get('concept_recap', '')
        sub = slide.get('thanks_subtitle', '')
        # v1.1: contact 字段格式化追加
        contact = slide.get('contact', {})
        contact_str = ''
        if contact:
            parts = [contact.get('company', ''), contact.get('date', ''),
                     contact.get('version', '')]
            contact_str = ' · '.join(p for p in parts if p)
        # 组合 closing_sub: concept_recap + thanks_subtitle + contact
        sub_parts = [p for p in [recap, sub, contact_str] if p]
        data['closing_sub'] = '<br>'.join(sub_parts) if sub_parts else ''

    elif stype == 'toc':
        data['title'] = slide.get('title', '目录')
        chapters = []
        for ch in slide.get('chapters', []):
            chapters.append({
                'num': ch.get('num', ''),
                'name': ch.get('name', ''),
                'name_en': ch.get('name_en', ''),
                'pages': ch.get('pages', ''),
            })
        data['chapters'] = chapters

    elif stype == 'chapter-divider':
        data['chapter_num'] = slide.get('chapter_num', '')
        data['chapter_name'] = slide.get('chapter_title', '')
        data['chapter_name_en'] = slide.get('chapter_concept', '')
        data['chapter_desc'] = slide.get('chapter_subtitle', '') or \
            slide.get('chapter_desc', '')
        asset = slide.get('asset', {})
        data['bg_image'] = convert_asset_path(
            asset.get('bg_image', ''), assets_base)

    elif stype == 'image-text-split':
        data['title'] = slide.get('title', '')
        data['subtitle'] = slide.get('title_en', '')
        content = slide.get('content', {})
        asset = slide.get('asset', {})
        data['image'] = convert_asset_path(
            asset.get('main_image', ''), assets_base)
        data['tag'] = content.get('callout', '')

        # 将 bullets/specs/timeline/key_metrics/functional_zones 组装成 cards
        cards = []
        bullets = content.get('bullets', [])
        if bullets:
            cards.append({
                'title': '',
                'text': '<br>'.join(bullets),
            })
        specs = content.get('specs', [])
        if specs:
            lines = [f'{s.get("label", "")}: {s.get("value", "")}'
                     for s in specs]
            cards.append({'title': '规格参数', 'text': '<br>'.join(lines)})
        timeline = content.get('timeline', [])
        if timeline:
            lines = [f'{t.get("stage", "")} ({t.get("year", "")}): '
                     f'{t.get("feature", "")}' for t in timeline]
            cards.append({'title': '演进历程', 'text': '<br>'.join(lines)})
        key_metrics = content.get('key_metrics', [])
        if key_metrics:
            lines = [f'{m.get("label", "")}: {m.get("value", "")}'
                     for m in key_metrics]
            cards.append({'title': '核心指标', 'text': '<br>'.join(lines)})
        zones = content.get('functional_zones', [])
        if zones:
            lines = [f'{z.get("name", "")}: {z.get("ratio", "")} '
                     f'@ {z.get("position", "")}' for z in zones]
            cards.append({'title': '功能分区', 'text': '<br>'.join(lines)})
        data['cards'] = cards if cards else [{'title': '', 'text': ''}]

    elif stype == 'three-cards':
        data['title'] = slide.get('title', '')
        # v1.1: concept_title/concept_desc 优先
        data['tag'] = slide.get('concept_title', '') or slide.get('title', '')
        data['subtitle'] = slide.get('concept_desc', '') or \
            slide.get('title_en', '')
        cards = slide.get('cards', [])
        data_cards = []
        for c in cards:
            items = []
            if c.get('desc'):
                items.append({'key': '', 'val': c['desc']})
            data_cards.append({
                'number': '',
                'unit': '',
                'label': c.get('title', ''),
                'items': items,
            })
        data['data_cards'] = data_cards
        photo_cards = []
        for c in cards:
            if c.get('icon'):
                photo_cards.append({
                    'image': convert_asset_path(c['icon'], assets_base),
                    'title': c.get('title', ''),
                    'tag': c.get('title_en', ''),
                })
        data['photo_cards'] = photo_cards
        # v1.1: 概念底图
        asset = slide.get('asset', {})
        if asset.get('bg_image'):
            data['bg_image'] = convert_asset_path(
                asset['bg_image'], assets_base)

    elif stype == 'comparison-table':
        data['title'] = slide.get('title', '')
        data['subtitle'] = slide.get('title_en', '')
        data['tag'] = slide.get('title', '')
        table = slide.get('table', {})
        data['headers'] = table.get('headers', [])
        hot_col = table.get('highlight_column', 1)
        rows_out = []
        for row in table.get('rows', []):
            indicator = row[0] if len(row) > 0 else ''
            if hot_col == 2:
                b_val = row[2] if len(row) > 2 else ''
                note_val = row[1] if len(row) > 1 else ''
            else:
                b_val = row[1] if len(row) > 1 else ''
                note_val = row[2] if len(row) > 2 else ''
            rows_out.append({
                'indicator': indicator,
                'b': b_val,
                'b_better': True,
                'note': note_val,
            })
        data['rows'] = rows_out
        # verdict → summary_cards
        verdict = slide.get('verdict', {})
        if verdict:
            data['summary_cards'] = [{
                'name': '推荐方案',
                'items': [{'k': verdict.get('recommended', ''),
                           'v': verdict.get('reason', '')}],
                'hot': True,
            }]
        else:
            data['summary_cards'] = []

    elif stype == 'data-profile':
        data['title'] = slide.get('title', '')
        data['subtitle'] = slide.get('title_en', '')
        data['tag'] = slide.get('title', '')
        dims = slide.get('dimensions', [])
        data_cards = []
        for d in dims:
            # 两种结构: {value, unit, desc} 或 {tag, metrics[]}
            if d.get('value') is not None:
                number = str(d.get('value', ''))
                unit = d.get('unit', '')
            elif d.get('tag'):
                number = ''
                unit = d.get('tag', '')
            else:
                number = ''
                unit = ''
            items = []
            if d.get('desc'):
                items.append({'key': '说明', 'val': d['desc']})
            for m in d.get('metrics', []):
                items.append({'key': m.get('label', ''),
                              'val': m.get('value', '')})
            data_cards.append({
                'number': number,
                'unit': unit,
                'label': d.get('category', ''),
                'items': items,
            })
        data['data_cards'] = data_cards
        # 主图映射到 photo_cards (如果有)
        asset = slide.get('asset', {})
        if asset.get('main_image'):
            data['photo_cards'] = [{
                'image': convert_asset_path(
                    asset['main_image'], assets_base),
                'title': '',
                'tag': '',
            }]
        else:
            data['photo_cards'] = []

    return {'id': sid, 'template': template, 'data': data}


# ================================================================
# 主转换: protocol.json → deck dict
# ================================================================
def convert_protocol(protocol: dict) -> dict:
    """将完整 page_protocol.json 转为 deck.yaml 格式的 dict"""
    project = protocol.get('project', {})
    assets_base = protocol.get('assets_base_path', 'assets/')
    slides = protocol.get('slides', [])
    total = len(slides)

    theme_name = THEME_MAP.get(project.get('theme', ''),
                               project.get('theme', 'blue-grey-business'))

    deck = {
        'project': {
            'name': project.get('name', ''),
            'name_en': project.get('name_en', ''),
            'type': '',
        },
        'theme': theme_name,
        'slides': [],
    }

    # concept 字段 (用于 gen_bg.py 分析)
    concepts = project.get('concept', [])
    if concepts:
        deck['concept'] = {
            'theme_words': concepts,
            'core_logic': '',
            'chapters': [],
        }

    for i, s in enumerate(slides, 1):
        deck['slides'].append(
            convert_slide(s, i, total, project, assets_base))

    return deck


# ================================================================
# CLI 入口
# ================================================================
def main():
    ap = argparse.ArgumentParser(
        description='PPT Layout Protocol v1.0 → PDF 渲染')
    ap.add_argument('--input', required=True,
                    help='page_protocol.json 路径')
    ap.add_argument('--output', default='',
                    help='输出 PDF 路径 (默认 build/<project>.pdf)')
    ap.add_argument('--skip-bg-gen', action='store_true',
                    help='跳过意向图生成 (COZE 沙箱无图像 API 时使用)')
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'✗ 协议文件不存在: {input_path}')
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        protocol = json.load(f)

    # 1. 校验
    errors = validate(protocol)
    if errors:
        print('✗ 协议校验失败:')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
    print(f'✓ 校验通过: {len(protocol["slides"])} 页')

    # 2. 转换为 deck 格式
    deck = convert_protocol(protocol)

    # 3. 写入 deck.yaml
    DECK_PATH.write_text(
        yaml.dump(deck, allow_unicode=True, sort_keys=False,
                  default_flow_style=False),
        encoding='utf-8')
    print(f'✓ deck.yaml 已生成')

    # 4. 渲染所有页面
    import subprocess
    py = sys.executable
    for s in deck['slides']:
        r = subprocess.run(
            [py, str(PROJECT_ROOT / 'scripts' / 'render_slide.py'),
             s['id']],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            print(f'  ⚠ {s["id"]} 渲染失败: {r.stderr[:200]}')
    print(f'✓ {len(deck["slides"])} 页已渲染')

    # 5. 意向图生成 (可选)
    if not args.skip_bg_gen:
        gen_bg = PROJECT_ROOT / 'scripts' / 'gen_bg.py'
        if gen_bg.exists():
            r = subprocess.run(
                [py, str(gen_bg), '--skip-gen', '--fill'],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            if r.returncode == 0:
                print('✓ 意向图路径已回填')
                # 重渲染受影响页
                for s in deck['slides']:
                    if s['template'] in ('cover', 'chapter-divider'):
                        subprocess.run(
                            [py, str(PROJECT_ROOT / 'scripts' /
                                     'render_slide.py'),
                             '--slide', s['id']],
                            capture_output=True, text=True,
                            cwd=str(PROJECT_ROOT))

    # 6. 构建 PDF
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    project_name = deck['project']['name']
    out = Path(args.output) if args.output else \
        BUILD_DIR / f'{project_name}.pdf'
    r = subprocess.run(
        [py, str(PROJECT_ROOT / 'scripts' / 'build_pdf.py'),
         '--output', str(out)],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    if r.returncode != 0:
        print(f'✗ PDF 构建失败: {r.stderr[:300]}')
        sys.exit(1)
    size_kb = out.stat().st_size // 1024
    print(f'✓ PDF 已生成: {out} ({size_kb} KB)')


if __name__ == '__main__':
    main()
