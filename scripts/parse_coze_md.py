"""
parse_coze_md.py - 解析 COZE 输出的 MD 草稿,填充 deck.yaml

适配 COZE 实际输出格式(基于安岳鞋服样本):
    # 概念主题：A · B · C
    **项目名称：** ...
    ## 核心逻辑
    **X → Y → Z**
    ## 章节拆解
    ### 第一章：名称（English Name）
    **页码：** P03 - P05
    **核心问题：** ...
    **关键内容：**
    - 要点1
    - 要点2
    ## 汇报话术
    ## 经济技术指标对比
    | 指标 | 方案一 | 方案二 |
    ## 页面结构清单（N页）
    | 页码 | 类型 | 标题 | 版式 |

使用：
    python parse_coze_md.py <input.md> [--project-type industrial_park|real_estate|other]
"""
import re
import sys
import argparse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'

# COZE 版式名 → 我的模板名映射
LAYOUT_MAP = {
    '封面': 'cover',
    '目录页': 'toc',
    '目录': 'toc',
    '章节过渡': 'chapter-divider',
    '图文分栏': 'split-image-text',
    '多卡片横排': 'multi-card-row',
    '四象限列表': 'quadrant-2x2',
    '时间线+图文': 'analysis-timeline',
    '大图+说明': 'split-image-text',
    '三卡片': 'multi-card-row',
    '方案呈现': 'scheme-present',
    '方案对比': 'scheme-compare',
    '结尾页': 'closing',
    '产品谱系': 'analysis-tech-stack',
}

# 页面类型 → 用途标记(用于后续排序/分组)
TYPE_MAP = {
    '封面': 'opening',
    '目录': 'opening',
    '章节过渡': 'divider',
    '内容': 'content',
    '过渡': 'transition',
    '方案': 'scheme',
    '分析': 'analysis',
    '对比': 'comparison',
    '结尾': 'ending',
}


def parse_header(md_text: str) -> dict:
    """解析文档头部: 概念主题 + 项目信息"""
    result = {}
    # 概念主题
    m = re.search(r'#\s*概念主题[:：]\s*(.+)', md_text)
    if m:
        theme_line = m.group(1).strip()
        # 支持 · / / · 分隔
        words = re.split(r'[·/\s·]+', theme_line)
        result['theme_words'] = [w for w in words if w]

    # 项目信息键值对 **键：** 值
    for key, label in [
        ('项目名称', 'name'),
        ('用地面积', 'land_area'),
        ('容积率', 'far'),
        ('总建筑面积', 'gfa'),
    ]:
        m = re.search(rf'\*\*{key}[:：]\*\*\s*(.+)', md_text)
        if m:
            result[label] = m.group(1).strip()
    return result


def parse_core_logic(md_text: str) -> str:
    """解析核心逻辑段"""
    # ## 核心逻辑 后面紧跟 **A → B → C**
    m = re.search(r'##\s*核心逻辑\s*\n+\*\*(.+?)\*\*', md_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ''


def parse_chapters(md_text: str) -> list:
    """解析章节拆解: 返回 [{id, name, name_en, page_range, problem, contents[]}]"""
    chapters = []
    # 每个章节从 ### 第X章：名称（English） 开始,到下一个 ### 或 ## 结束
    pattern = re.compile(
        r'###\s*第([一二三四五六七八九十]+)章[:：]\s*(.+?)(?:（(.+?)）)?\s*\n'
        r'(.*?)(?=\n###|\n##|\Z)',
        re.DOTALL,
    )
    cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    for m in pattern.finditer(md_text):
        num_cn = m.group(1)
        name = m.group(2).strip()
        name_en = (m.group(3) or '').strip()
        body = m.group(4)

        page_range = ''
        problem = ''
        contents = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            pm = re.match(r'\*\*页码[:：]\*\*\s*(.+)', line)
            if pm:
                page_range = pm.group(1).strip()
                continue
            pm = re.match(r'\*\*核心问题[:：]\*\*\s*(.+)', line)
            if pm:
                problem = pm.group(1).strip()
                continue
            if line.startswith('- '):
                contents.append(line[2:].strip())

        chapters.append({
            'id': f'ch{cn_num.get(num_cn, len(chapters)+1)}',
            'num': cn_num.get(num_cn, len(chapters)+1),
            'name': name,
            'name_en': name_en,
            'page_range': page_range,
            'problem': problem,
            'contents': contents,
        })
    return chapters


def parse_narrative(md_text: str) -> str:
    """解析汇报话术(保留为纯文本)"""
    m = re.search(r'##\s*汇报话术\s*\n(.*?)(?=\n##|\Z)', md_text, re.DOTALL)
    return m.group(1).strip() if m else ''


def parse_indicator_table(md_text: str) -> list:
    """解析经济技术指标对比表: 返回 [{indicator, scheme_a, scheme_b}]"""
    m = re.search(r'##\s*经济技术指标对比\s*\n+(\|.+\|(?:\n\|.+\|)+)', md_text)
    if not m:
        return []
    table_text = m.group(1)
    rows = []
    for line in table_text.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 3 or cells[0] in ('指标', '---', '------'):
            continue
        if set(cells[0]) <= set('-:'):  # 对齐行
            continue
        rows.append({'indicator': cells[0], 'scheme_a': cells[1], 'scheme_b': cells[2]})
    return rows


def parse_page_list(md_text: str) -> list:
    """解析页面结构清单表格: 返回 [{page_num, type, title, layout}]"""
    m = re.search(r'##\s*页面结构清单.*?\n+(\|.+\|(?:\n\|.+\|)+)', md_text, re.DOTALL)
    if not m:
        return []
    table_text = m.group(1)
    pages = []
    for line in table_text.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4:
            continue
        if cells[0] in ('页码',) or set(cells[0]) <= set('-:'):
            continue
        pages.append({
            'page_num': cells[0],
            'type': cells[1],
            'title': cells[2],
            'layout': cells[3],
        })
    return pages


def map_to_slides(pages: list, chapters: list, indicators: list) -> list:
    """把页面结构清单 + 章节内容映射成 deck.yaml 的 slides"""
    slides = []
    for idx, p in enumerate(pages, 1):
        slide_id = f'slide_{idx:02d}'
        template = LAYOUT_MAP.get(p['layout'], 'split-image-text')
        page_type = TYPE_MAP.get(p['type'], 'content')

        # 推断所属章节: 章节过渡页的标题含章节号
        chapter_id = ''
        if page_type == 'divider':
            m = re.search(r'([0-9]+)', p['title'])
            if m:
                chapter_id = f'ch{m.group(1)}'
        else:
            # 找最近的章节过渡页所属章节
            for prev in reversed(slides):
                if prev.get('_page_type') == 'divider':
                    chapter_id = prev.get('chapter', '')
                    break

        # 准备 data
        data = {
            'title': p['title'],
            'tag': '',
            'subtitle': '',
            'project_name_en': '',
            'page_num': str(idx),
        }

        # 把对应章节的关键内容作为候选要点
        ch = next((c for c in chapters if c['id'] == chapter_id), None)
        if ch:
            data['tag'] = ch['name_en']
            data['subtitle'] = ch['name']
            if ch['contents']:
                data['points'] = ch['contents']
            if ch['problem']:
                data['problem'] = ch['problem']

        # 方案对比页: 注入经济技术指标
        if template == 'scheme-compare' and indicators:
            data['schemes'] = [
                {
                    'name': '方案一',
                    'name_en': 'SCHEME 01',
                    'featured': False,
                    'metrics': [
                        {'key': ind['indicator'], 'val': ind['scheme_a'], 'highlight': False}
                        for ind in indicators
                    ],
                },
                {
                    'name': '方案二',
                    'name_en': 'SCHEME 02',
                    'featured': True,
                    'metrics': [
                        {'key': ind['indicator'], 'val': ind['scheme_b'], 'highlight': False}
                        for ind in indicators
                    ],
                },
            ]

        slide = {
            'id': slide_id,
            'chapter': chapter_id,
            'template': template,
            'title': p['title'],
            'status': 'draft',
            'assets': [],
            'last_modified': '',
            'notes': f"COZE类型={p['type']} | 版式={p['layout']}",
            'data': data,
            '_page_type': page_type,  # 临时字段,写回前清理
        }
        slides.append(slide)
    return slides


def merge_into_deck(parsed: dict, project_type: str, deck_path: Path):
    deck = {}
    if deck_path.exists():
        with open(deck_path, 'r', encoding='utf-8') as f:
            deck = yaml.safe_load(f) or {}

    # 项目元信息
    proj = parsed['header']
    deck['project'] = {
        'name': proj.get('name', ''),
        'name_en': '',
        'type': project_type,
        'force_intent': False,
        'date': '',
        'audience': '甲方/评委',
        'tone': 'high_business',
        'land_area': proj.get('land_area', ''),
        'far': proj.get('far', ''),
        'gfa': proj.get('gfa', ''),
    }
    deck['theme'] = deck.get('theme', 'blue-grey-coze')

    # 概念主旨
    deck['concept'] = {
        'theme_words': proj.get('theme_words', []),
        'core_logic': parsed['core_logic'],
        'chapters': [
            {'word': c['name'], 'problem': c['problem'], 'content': '、'.join(c['contents'])}
            for c in parsed['chapters']
        ],
        'narrative': parsed['narrative'],
    }

    # 章节列表
    deck['narrative_chapters'] = [
        {'id': c['id'], 'name': c['name'], 'name_en': c['name_en']}
        for c in parsed['chapters']
    ]

    # 口号页插入位置(产业园区默认不触发,保留配置)
    deck['intent_page_slots'] = deck.get('intent_page_slots', [
        {'after_chapter': 'ch3', 'type': 'intent_bigtext'},
        {'in_chapter': 'ch4', 'type': 'intent_three_claim'},
    ])

    # 页面清单(清理临时字段)
    slides = []
    for s in parsed['slides']:
        s.pop('_page_type', None)
        slides.append(s)
    deck['slides'] = slides

    # 构建状态
    deck['build'] = {
        'engine': 'playwright',
        'output_dir': 'build/',
        'last_build': '',
        'last_build_pdf': '',
        'last_build_pptx': '',
    }

    with open(deck_path, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f'✓ deck.yaml 已更新: {deck_path}')
    print(f'  项目: {deck["project"]["name"]}')
    print(f'  类型: {project_type}')
    print(f'  概念词: {deck["concept"]["theme_words"]}')
    print(f'  章节数: {len(parsed["chapters"])}')
    print(f'  页面数: {len(slides)}')


def main():
    ap = argparse.ArgumentParser(description='解析 COZE MD 草稿到 deck.yaml')
    ap.add_argument('input_md', help='COZE 输出的 MD 文件路径')
    ap.add_argument('--project-type', default='industrial_park',
                    choices=['industrial_park', 'real_estate', 'other'])
    args = ap.parse_args()

    md_path = Path(args.input_md)
    if not md_path.exists():
        print(f'✗ 文件不存在: {md_path}')
        sys.exit(1)

    md_text = md_path.read_text(encoding='utf-8')

    parsed = {
        'header': parse_header(md_text),
        'core_logic': parse_core_logic(md_text),
        'chapters': parse_chapters(md_text),
        'narrative': parse_narrative(md_text),
        'indicators': parse_indicator_table(md_text),
        'page_list': parse_page_list(md_text),
    }
    parsed['slides'] = map_to_slides(parsed['page_list'], parsed['chapters'], parsed['indicators'])

    merge_into_deck(parsed, args.project_type, DECK_PATH)


if __name__ == '__main__':
    main()
