"""
parse_v2_pdf.py - 反解析 v2.pdf 提取 8 章页面结构,生成新 deck.yaml

针对「安岳县柠檬冷链共享仓建设项目」v2.pdf (54 页) 8 章结构:
    01 项目背景与场地研判 PROJECT BACKGROUND & SITE ANALYSIS
    02 市场背景与设计依据 MARKET CONTEXT & DESIGN BASIS
    03 概念主旨       CONCEPT THEME
    04 方案呈现·效果图 SCHEME PRESENTATION
    05 设计分析       DESIGN ANALYSIS
    06 二期规划(远期)  FUTURE PHASE
    07 技术图纸       DESIGN DRAWINGS
    08 设计说明       DESIGN NOTES

用户拍板:
    - 方案2 → 改名「设计方案」(推荐高亮)
    - 方案1 → 改名「二期规划」(远期拓展倡议分析,不作对比)
    - project_type=industrial_park,不触发口号页(force_intent=false)
    - 效果图4张已抽到 assets/images/renders/

使用:
    python parse_v2_pdf.py
"""
import sys
import yaml
import pymupdf
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
V2_PDF = Path(r'E:\TRAE\l-柠檬冷链物流\20260920合--安岳县柠檬冷链共享仓建设项目v2.pdf')

# —— 8 章定义 ——
CHAPTERS = [
    {'id': 'ch1', 'num': '01', 'name': '项目背景与场地研判',
     'name_en': 'PROJECT BACKGROUND & SITE ANALYSIS', 'page_range': 'P04 - P10'},
    {'id': 'ch2', 'num': '02', 'name': '市场背景与设计依据',
     'name_en': 'MARKET CONTEXT & DESIGN BASIS', 'page_range': 'P11 - P15'},
    {'id': 'ch3', 'num': '03', 'name': '概念主旨',
     'name_en': 'CONCEPT THEME', 'page_range': 'P16 - P18'},
    {'id': 'ch4', 'num': '04', 'name': '方案呈现·效果图',
     'name_en': 'SCHEME PRESENTATION', 'page_range': 'P19 - P25'},
    {'id': 'ch5', 'num': '05', 'name': '设计分析',
     'name_en': 'DESIGN ANALYSIS', 'page_range': 'P26 - P42'},
    {'id': 'ch6', 'num': '06', 'name': '二期规划(远期)',
     'name_en': 'FUTURE PHASE', 'page_range': 'P43 - P47'},
    {'id': 'ch7', 'num': '07', 'name': '技术图纸',
     'name_en': 'DESIGN DRAWINGS', 'page_range': 'P48 - P53'},
    {'id': 'ch8', 'num': '08', 'name': '设计说明',
     'name_en': 'DESIGN NOTES', 'page_range': 'P54'},
]

# —— 54 页映射 (page_num → 章节+模板+标题+备注) ——
# 模板选项: cover / toc / chapter-divider / split-image-text / multi-card-row /
#          quadrant-2x2 / scheme-present / scheme-compare / compare-table /
#          analysis-* / closing / intent-* (本次不触发)
PAGES = [
    # p1 封面
    (1,  '',   'cover',             '安岳县柠檬冷链共享仓建设项目', '封面'),
    # p2 资质页(项目概况)
    (2,  '',   'split-image-text',  '设计/规划资质',           '封皮2·资质'),
    # p3 目录
    (3,  '',   'toc',               'CONTENTS',                '目录'),
    # === ch1 01 项目背景与场地研判 ===
    (4,  'ch1','chapter-divider',   '01 项目背景与场地研判',     '章节过渡'),
    (5,  'ch1','multi-card-row',    '1.1 项目定位与区域背景',    '图文+数据卡'),
    (6,  'ch1','split-image-text',  '1.1 上位规划分析',         '图文分栏'),
    (7,  'ch1','split-image-text',  '1.2 场地现状分析(区位)',    '图文分栏'),
    (8,  'ch1','split-image-text',  '1.2 场地现状分析(卫星)',    '图文分栏'),
    (9,  'ch1','split-image-text',  '1.2 场地现状分析(分 phase)', '图文分栏'),
    (10, 'ch1','split-image-text',  '1.2 场地高差·现状条件',    '图文分栏'),
    # === ch2 02 市场背景与设计依据 ===
    (11, 'ch2','chapter-divider',   '02 市场背景与设计依据',     '章节过渡'),
    (12, 'ch2','split-image-text',  '2.1 案例分析(蒲江/鑫柠乐)',  '图文分栏'),
    (13, 'ch2','split-image-text',  '2.1 案例分析(续)',         '图文分栏'),
    (14, 'ch2','quadrant-2x2',      '2.2 功能配比数据分析',     '四象限/表格'),
    (15, 'ch2','multi-card-row',    '2.3 物流区尺度参数',       '多数据卡'),
    # === ch3 03 概念主旨 ===
    (16, 'ch3','chapter-divider',   '03 概念主旨',             '章节过渡'),
    (17, 'ch3','intent-bigtext',    '以鲜为诺·共享链通',        '概念主旨页(intent_bigtext 占位,force_intent=false 不会渲染但保留)'),
    (18, 'ch3','split-image-text',  '概念推导·三词拆解',        '图文分栏'),
    # === ch4 04 方案呈现·效果图 ===
    (19, 'ch4','chapter-divider',   '04 方案呈现·效果图',       '章节过渡'),
    (20, 'ch4','scheme-present',    '效果图·鸟瞰1',            '方案呈现'),
    (21, 'ch4','scheme-present',    '效果图·鸟瞰2',            '方案呈现'),
    (22, 'ch4','scheme-present',    '效果图·透视1',            '方案呈现'),
    (23, 'ch4','scheme-present',    '效果图·透视2',            '方案呈现'),
    (24, 'ch4','split-image-text',  '总图+经济技术指标',        '图文分栏'),
    (25, 'ch4','compare-table',     '面积明细·设计方案指标',     '对比表(仅设计方案)'),
    # === ch5 05 设计分析 ===
    (26, 'ch5','chapter-divider',   '05 设计分析',             '章节过渡'),
    (27, 'ch5','split-image-text',  '5.1 功能分析',            '图文分栏'),
    (28, 'ch5','split-image-text',  '5.2 原料进出流线分析',     '图文分栏'),
    (29, 'ch5','split-image-text',  '5.3 生产流线分析',        '图文分栏'),
    (30, 'ch5','split-image-text',  '5.4 成品货车进场流线',     '图文分栏'),
    (31, 'ch5','split-image-text',  '5.5 成品货车驶离流线',     '图文分栏'),
    (32, 'ch5','split-image-text',  '5.6 规划间距分析',        '图文分栏'),
    (33, 'ch5','split-image-text',  '5.7 消防车道分析',        '图文分栏'),
    (34, 'ch5','split-image-text',  '5.8 地面停车分析',        '图文分栏'),
    (35, 'ch5','split-image-text',  '5.9 竖向分析',            '图文分栏'),
    (36, 'ch5','split-image-text',  '5.10 边坡设计分析',       '图文分栏'),
    (37, 'ch5','split-image-text',  '5.11 层高分析',           '图文分栏'),
    (38, 'ch5','split-image-text',  '5.12 管网分析',           '图文分栏'),
    (39, 'ch5','split-image-text',  '5.13 防火分区分析',        '图文分栏'),
    (40, 'ch5','split-image-text',  '5.14 立面材质·设计方案',    '图文分栏(原06对比方案-方案二改造)'),
    (41, 'ch5','split-image-text',  '5.15 双碳·低碳生态',       '图文分栏'),
    (42, 'ch5','quadrant-2x2',     '5.16 技术措施',           '四象限/卡片'),
    # === ch6 06 二期规划(远期) ===
    (43, 'ch6','chapter-divider',   '06 二期规划(远期)',        '章节过渡'),
    (44, 'ch6','split-image-text',  '6.1 远期(二期)规划分析',   '图文分栏'),
    (45, 'ch6','split-image-text',  '6.2 远期基础设施组织',     '图文分栏'),
    (46, 'ch6','scheme-present',    '效果图A·二期鸟瞰',         '方案呈现'),
    (47, 'ch6','scheme-present',    '效果图A·二期透视',         '方案呈现'),
    # === ch7 07 技术图纸 ===
    (48, 'ch7','chapter-divider',   '07 技术图纸',             '章节过渡'),
    (49, 'ch7','scheme-present',    '图纸·总平面图',           '方案呈现'),
    (50, 'ch7','scheme-present',    '图纸·一层平面图',         '方案呈现'),
    (51, 'ch7','scheme-present',    '图纸·夹层平面图',         '方案呈现'),
    (52, 'ch7','scheme-present',    '图纸·二层平面图',         '方案呈现'),
    (53, 'ch7','scheme-present',    '图纸·1-1剖面图',         '方案呈现'),
    # === ch8 08 设计说明 ===
    (54, 'ch8','closing',           '感谢聆听',               '结尾页'),
]

# —— 效果图路径映射 (page_num → assets 路径) ——
RENDER_IMAGES = {
    20: '../assets/images/renders/鸟瞰1.png',
    21: '../assets/images/renders/鸟瞰2.png',
    22: '../assets/images/renders/透视1.png',
    23: '../assets/images/renders/透视2.png',
    # 46/47 二期效果图暂用透视图占位(用户未单独提供二期效果)
    46: '../assets/images/renders/鸟瞰1.png',
    47: '../assets/images/renders/透视1.png',
}


def build_slide_data(page_num: int, chapter_id: str, template: str,
                     title: str, pdf_text: str, img_count: int) -> dict:
    """根据模板类型生成 slide.data 字段"""
    base = {
        'title': title,
        'tag': '',
        'subtitle': '',
        'project_name_en': '',
        'page_num': str(page_num),
    }
    if template == 'cover':
        base.update({
            'project_name': '安岳县柠檬冷链共享仓建设项目',
            'project_name_en': '',
            'bg_image': '../assets/images/bg/cover.jpg',
        })
    elif template == 'toc':
        base['chapters'] = [
            {'num': c['num'], 'name': c['name'], 'name_en': c['name_en'],
             'pages': c['page_range']}
            for c in CHAPTERS
        ]
    elif template == 'chapter-divider':
        ch = next(c for c in CHAPTERS if c['id'] == chapter_id)
        base.update({
            'bg_image': '../assets/images/bg/divider.jpg',
            'chapter_num': ch['num'],
            'chapter_name': ch['name'],
            'chapter_desc': '',
            'chapter_name_en': ch['name_en'],
        })
    elif template == 'scheme-present':
        # 效果图/图纸页: 接入图片
        img = RENDER_IMAGES.get(page_num, '')
        base.update({
            'scheme_num': str(page_num),
            'scheme_name': title,
            'scheme_name_en': '',
            'image': img,
            'description': '',
            'metrics': [],
        })
    elif template == 'compare-table':
        # 面积明细表: 后续 parse_excel.py 回填
        base.update({
            'table_title': '面积明细·设计方案指标',
            'columns': [
                {'key': 'name', 'label': '建筑名称'},
                {'key': 'underground', 'label': '地下层'},
                {'key': 'f1', 'label': '1层'},
                {'key': 'f2', 'label': '2层(夹层)'},
                {'key': 'subtotal', 'label': '面积小计'},
                {'key': 'base', 'label': '基底面积'},
            ],
            'rows': [],
            'highlighted_scheme': '设计方案',
        })
    elif template == 'multi-card-row':
        base['data_cards'] = []
        base['photo_cards'] = [{'image': '', 'title': '配图位', 'tag': ''}]
    elif template == 'quadrant-2x2':
        base['intro'] = ''
        base['quadrants'] = [
            {'title': '要点 1', 'points': []},
            {'title': '要点 2', 'points': []},
            {'title': '要点 3', 'points': []},
            {'title': '要点 4', 'points': []},
        ]
    elif template == 'closing':
        base.update({
            'closing_text': '鲜藏·共享·链通',
            'closing_sub': 'THANKS',
            'project_name': '安岳县柠檬冷链共享仓建设项目',
        })
    elif template == 'intent-bigtext':
        # 概念主旨页: force_intent=false 不会渲染,但保留 data
        base['big_text'] = '鲜藏·共享·链通'
    else:
        # split-image-text 默认
        base['cards'] = [{'title': title, 'text': ''}]
        base['image'] = ''
    return base


def main():
    if not V2_PDF.exists():
        print(f'[ERR] v2.pdf 不存在: {V2_PDF}', file=sys.stderr)
        sys.exit(1)

    # 1. 打开 v2.pdf 提取每页元数据
    doc = pymupdf.open(V2_PDF)
    if len(doc) != 54:
        print(f'[WARN] v2.pdf 实际页数 {len(doc)} 与预期 54 不符,仍按预定义映射继续')

    pdf_meta = {}
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        img_count = len(page.get_images())
        # 首行非空文本(去掉换行)
        first_line = ''
        for ln in text.splitlines():
            ln = ln.strip()
            if ln:
                first_line = ln
                break
        pdf_meta[i] = {
            'first_line': first_line,
            'img_count': img_count,
            'text_len': len(text),
        }
    doc.close()

    # 2. 构建 slides 列表
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    slides = []
    for page_num, chapter_id, template, title, notes in PAGES:
        meta = pdf_meta.get(page_num, {})
        data = build_slide_data(page_num, chapter_id, template, title,
                               meta.get('first_line', ''),
                               meta.get('img_count', 0))
        slide = {
            'id': f'slide_{page_num:02d}',
            'chapter': chapter_id,
            'template': template,
            'title': title,
            'status': 'draft',
            'assets': [],
            'last_modified': now,
            'notes': f"{notes} | pdf_p{page_num} img={meta.get('img_count', '?')}",
            'data': data,
            'page_num': str(page_num),
        }
        slides.append(slide)

    # 3. 装配 deck
    deck = {
        'project': {
            'name': '安岳县柠檬冷链共享仓建设项目',
            'name_en': '',
            'type': 'industrial_park',
            'force_intent': False,
            'date': '',
            'audience': '甲方/评委',
            'tone': 'high_business',
            'land_area': '',
            'far': '',
            'gfa': '',
        },
        'theme': 'blue-grey-coze',
        'concept': {
            'theme_words': ['鲜藏', '共享', '链通'],
            'core_logic': '鲜藏(能力) → 共享(模式) → 链通(目标)',
            'chapters': [
                {'word': c['name'],
                 'problem': '',
                 'content': c['page_range']}
                for c in CHAPTERS
            ],
            'narrative': '',
        },
        'narrative_chapters': [
            {'id': c['id'], 'name': c['name'], 'name_en': c['name_en']}
            for c in CHAPTERS
        ],
        # intent_page_slots 保留但 force_intent=false → 不会触发口号页
        'intent_page_slots': [
            {'after_chapter': 'ch3', 'type': 'intent_bigtext'},
        ],
        'slides': slides,
        'build': {
            'engine': 'playwright',
            'output_dir': 'build/',
            'last_build': '',
            'last_build_pdf': '',
            'last_build_pptx': '',
        },
        '_total_pages': len(slides),
        '_source': f'parse_v2_pdf.py @ {now} | source={V2_PDF.name}',
    }

    # 4. 写入 deck.yaml(备份旧文件)
    backup = DECK_PATH.with_suffix('.yaml.bak')
    if DECK_PATH.exists():
        DECK_PATH.rename(backup)
        print(f'[OK] 旧 deck.yaml 已备份到 {backup.name}')

    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(deck, f, allow_unicode=True, sort_keys=False,
                       width=100, default_flow_style=False)
    print(f'[OK] 新 deck.yaml 已生成: {DECK_PATH}')
    print(f'     总页数: {len(slides)}')
    print(f'     章节数: {len(CHAPTERS)}')
    print(f'     设计方案效果图已接入: {sum(1 for p in [20,21,22,23] if RENDER_IMAGES.get(p))}/4')
    print()
    print('[下一步]')
    print('  1. 跑 parse_excel.py 回填 p25 面积明细表')
    print('  2. 跑 fill_content.py 填充其余文字内容')
    print('  3. 跑 render_slide.py --all 渲染所有页')
    print('  4. 跑 build_pdf.py 生成 PDF')


if __name__ == '__main__':
    main()
