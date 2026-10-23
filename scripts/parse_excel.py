"""
parse_excel.py - 接入 Excel 4 sheet 指标数据,回填 deck.yaml

数据源: E:\\TRAE\\l-柠檬冷链物流\\20260915总平及平面图.xlsx (4 sheet)
    - '1期（暂时没更新）'        → 旧一期数据,本次不用
    - '综合经济技术指标(方案2）'  → 设计方案(推荐)
    - '综合经济技术指标(方案1）'  → 二期规划(远期)
    - 'Sheet1'                  → 空,跳过

用户拍板:
    - 方案2 → 改名「设计方案」(推荐高亮)
    - 方案1 → 改名「二期规划」(远期拓展倡议,不作对比)
    - p25 compare-table 模板改为「指标/设计方案/备注」三列(不做两方案对比)
    - p44 split-image-text 注入二期规划远期指标数据

使用:
    python parse_excel.py
"""
import sys
import yaml
import openpyxl
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
EXCEL_PATH = Path(r'E:\TRAE\l-柠檬冷链物流\20260915总平及平面图.xlsx')

SHEET_DESIGN = '综合经济技术指标(方案2）'   # 设计方案(推荐)
SHEET_FUTURE = '综合经济技术指标(方案1）'   # 二期规划(远期)


def parse_building_table(ws, max_row: int = 40) -> list:
    """解析「建筑单体系数表格」段,返回 [{floor, name, underground, f1, f2, subtotal, base}]
    列映射(基于方案2/方案1 sheet 实测):
        col7=楼号 col8=建筑名称 col9=地下层 col10=1层 col11=2层夹层
        col17=面积小计 col20=基底面积
    子项行(原料取袋区等)floor为空时,继承上一行楼号
    """
    rows = []
    headers_done = False
    last_floor = ''
    in_underground = False
    for r in range(1, max_row + 1):
        floor = ws.cell(r, 7).value      # 楼号/地下室
        name = ws.cell(r, 8).value       # 建筑名称
        if not headers_done:
            if floor == '楼号':
                headers_done = True
            continue
        if not name:
            # 空行/纯汇总行: 跳过,但保持 in_underground 状态
            continue
        # 楼号变化: 主表项(1/2) 或 地下室
        if floor is not None and floor != '':
            if isinstance(floor, str) and '地下室' in str(floor):
                in_underground = True
                last_floor = '地下室'
            else:
                in_underground = False
                last_floor = str(floor).strip()
        # 子项(无 floor)继承 last_floor
        cur_floor = str(floor).strip() if floor else last_floor
        # 跳过整层小计行(col17有值 col8无名称/为空白) -- 上面已过滤
        row_data = {
            'floor': cur_floor,
            'name': str(name).strip(),
            'underground': _num(ws.cell(r, 9).value),
            'f1': _num(ws.cell(r, 10).value),
            'f2': _num(ws.cell(r, 11).value),
            'subtotal': _num(ws.cell(r, 18).value),   # col18=面积小计
            'base': _num(ws.cell(r, 21).value),       # col21=基底面积
        }
        # 至少有一个面积值才收录
        if any([row_data['underground'], row_data['f1'], row_data['f2'],
                row_data['subtotal'], row_data['base']]):
            rows.append(row_data)
    return rows


def parse_indicator_table(ws, max_row: int = 90) -> dict:
    """解析「冷链项目综合经济技术指标」段,返回 {项目名: {val, note}}
    列映射(基于方案2/方案1 sheet 实测):
        col3=项目名/其中/小计 col4=子项名 col5=指标值 col6=备注
    """
    result = {}
    in_section = False
    for r in range(1, max_row + 1):
        col_c = ws.cell(r, 3).value  # 项目名/其中
        col_d = ws.cell(r, 4).value  # 子项名
        col_e = ws.cell(r, 5).value  # 指标值
        col_f = ws.cell(r, 6).value  # 备注
        if not in_section:
            if col_c and '冷链项目综合经济技术指标' in str(col_c):
                in_section = True
            continue
        # 表头行: col_c='项目' col_e='指标'
        if col_c == '项目' and col_e == '指标':
            continue
        if not col_c:
            continue
        # 子项(col_c='其中' 或 '其中（xxx）'): col_d=子项名 col_e=值 col_f=备注
        if isinstance(col_c, str) and col_c.startswith('其中'):
            if col_d and col_e is not None and col_e != '':
                result[str(col_d).strip()] = {
                    'val': _num_str(col_e),
                    'note': _num_str(col_f) if col_f else '',
                }
            continue
        if col_c in ('小计', '合计'):
            continue
        # 主项
        if col_e is not None and col_e != '':
            result[str(col_c).strip()] = {
                'val': _num_str(col_e),
                'note': _num_str(col_f) if col_f else '',
            }
    return result


def _num(v):
    """转数值或空字符串"""
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v).strip()


def _num_str(v) -> str:
    """转字符串数值,带单位"""
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)):
        # 保留两位小数,去除多余 .0
        if abs(v - round(v)) < 0.001:
            return str(int(round(v)))
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    return str(v).strip()


def fmt_area(v) -> str:
    """格式化面积数值,加 ㎡ 单位"""
    s = _num_str(v)
    if s and not s.endswith('㎡') and not s.endswith('亩') and not s.endswith('%') \
            and not s.endswith('辆') and not s.endswith('m'):
        return f'{s} ㎡'
    return s


def build_p25_compare_table(design_ind: dict, design_buildings: list) -> dict:
    """构建 p25 compare-table 的 data 字段
    三列: 指标 | 设计方案 | 备注
    summary_cards: 两张定位卡(一期现状 + 二期规划远期)
    """
    # 主表行 - 从综合指标中按指定顺序提取
    indicator_order = [
        ('用地面积', '用地面积'),
        ('总建筑面积', '总建筑面积'),
        ('地上总建筑面积', '地上总建筑面积'),
        ('地上计容建筑面积', '地上计容建筑面积'),
        ('地下建筑面积', '地下建筑面积'),
        ('容积率', '容积率'),
        ('建筑基底', '建筑基底'),
        ('建筑密度', '建筑密度'),
        ('行政办公及生活服务区面积占比', '行政办公占比'),
        ('车位', '车位'),
        ('非机动停车区', '非机动停车区'),
    ]
    rows = []
    for key, label in indicator_order:
        item = design_ind.get(key)
        if not item:
            continue
        val = item['val']
        note = item.get('note', '')
        # 容积率/建筑密度: 保留小数
        if key == '容积率':
            try:
                val = f'{float(val):.2f}'
            except (TypeError, ValueError):
                pass
        elif key == '建筑密度':
            try:
                val = f'{float(val)*100:.1f}%' if float(val) < 1 else f'{float(val):.1f}%'
            except (TypeError, ValueError):
                pass
        elif key in ('用地面积', '总建筑面积', '地上总建筑面积', '地上计容建筑面积',
                     '地下建筑面积', '建筑基底', '非机动停车区'):
            val = fmt_area(val)
        elif key == '车位':
            val = f'{val} 辆' if val else ''
        rows.append({
            'indicator': label,
            'a': '',  # 不做对比,a 列留空
            'b': val,
            'b_better': True,  # 高亮设计方案的值
            'note': note,
        })

    # summary_cards - 两张定位卡
    summary_cards = [
        {
            'name': '设计方案 · 一期建设',
            'hot': True,
            'items': [
                {'k': '用地面积', 'v': fmt_area(design_ind.get('用地面积', {}).get('val', ''))},
                {'k': '总建筑面积', 'v': fmt_area(design_ind.get('总建筑面积', {}).get('val', ''))},
                {'k': '容积率', 'v': _num_str(design_ind.get('容积率', {}).get('val', ''))},
                {'k': '建筑密度', 'v': f"{_num_str(design_ind.get('建筑密度', {}).get('val', ''))}%"},
                {'k': '车位', 'v': f"{_num_str(design_ind.get('车位', {}).get('val', ''))} 辆"},
            ],
        },
        # 二期规划卡 - 在 parse 完 future_ind 后填充,这里先放占位
    ]
    return {
        'title': '设计方案综合经济技术指标',
        'tag': 'DESIGN SCHEME',
        'subtitle': '安岳县柠檬冷链共享仓建设项目 · 一期',
        'project_name_en': '',
        'page_num': '25',
        'headers': ['指标', '设计方案', '备注'],
        'rows': rows,
        'summary_cards': summary_cards,  # 会被 main() 后续补 future 卡
        'highlighted_scheme': '设计方案',
    }


def build_p44_future_phase(future_ind: dict, future_buildings: list) -> dict:
    """构建 p44 二期规划分析页 data (split-image-text)"""
    cards = [
        {'title': '二期规划核心指标',
         'text': (f"用地面积 {fmt_area(future_ind.get('用地面积', {}).get('val', ''))}（42.09亩）"
                  f"；总建筑面积 {fmt_area(future_ind.get('总建筑面积', {}).get('val', ''))}"
                  f"；地上计容 {fmt_area(future_ind.get('地上计容建筑面积', {}).get('val', ''))}"
                  f"；地下 {fmt_area(future_ind.get('地下建筑面积', {}).get('val', ''))}。")},
        {'title': '远期拓展要点',
         'text': '远期土地供应后的拓展倡议分析；二期生产区以厂房 18,229.69 ㎡为主体，'
                 '辅以厂房办公 398.95 ㎡、污水设备房 115.2 ㎡、卫生间 60.8 ㎡、'
                 '配套用房 57.62 ㎡、冷库柴发 159.82 ㎡；地下设备用房 601.62 ㎡。'
                 '本期作为远期规划建议，不与设计方案做对比。'},
    ]
    return {
        'title': '6.1 远期(二期)规划分析',
        'tag': 'FUTURE PHASE',
        'subtitle': '远期土地供应后的拓展倡议',
        'project_name_en': '',
        'page_num': '44',
        'cards': cards,
        'image': '',
    }


def update_deck(design_ind: dict, design_buildings: list,
                future_ind: dict, future_buildings: list):
    """更新 deck.yaml 中 p25 / p44 / p45 数据"""
    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 补充 future 卡到 p25 summary_cards
    p25_data = build_p25_compare_table(design_ind, design_buildings)
    p25_data['summary_cards'].append({
        'name': '二期规划 · 远期拓展',
        'hot': False,
        'items': [
            {'k': '用地面积', 'v': fmt_area(future_ind.get('用地面积', {}).get('val', ''))},
            {'k': '总建筑面积', 'v': fmt_area(future_ind.get('总建筑面积', {}).get('val', ''))},
            {'k': '容积率', 'v': _num_str(future_ind.get('容积率', {}).get('val', ''))},
            {'k': '建筑密度', 'v': f"{_num_str(future_ind.get('建筑密度', {}).get('val', ''))}%"},
            {'k': '车位', 'v': f"{_num_str(future_ind.get('车位', {}).get('val', ''))} 辆"},
        ],
    })

    p44_data = build_p44_future_phase(future_ind, future_buildings)

    # p45 远期基础设施组织 - 补一行总览数据
    p45_data = {
        'title': '6.2 远期基础设施组织',
        'tag': 'FUTURE PHASE',
        'subtitle': '先地下后地上 · 先主干后分支',
        'project_name_en': '',
        'page_num': '45',
        'cards': [
            {'title': '道路与消防组织',
             'text': '场地环路一次成形/分段闭合，保证当期货运与人行可达、客货互不交叉。'
                     '消防车道环通、消防水源与扑救面随首期同步投运。'},
            {'title': '二期指标数据',
             'text': f"二期用地 {fmt_area(future_ind.get('用地面积', {}).get('val', ''))}"
                     f"；总建筑面积 {fmt_area(future_ind.get('总建筑面积', {}).get('val', ''))}"
                     f"；地上计容 {fmt_area(future_ind.get('地上计容建筑面积', {}).get('val', ''))}"
                     f"；容积率 {_num_str(future_ind.get('容积率', {}).get('val', ''))}"
                     f"；建筑密度 {future_ind.get('建筑密度', {}).get('val', '')}。"},
        ],
        'image': '',
    }

    # 找到 p25/p44/p45 并替换 data + 模板
    for slide in deck.get('slides', []):
        pn = int(slide.get('page_num', 0))
        if pn == 25:
            slide['template'] = 'compare-table'
            slide['title'] = p25_data['title']
            slide['data'] = p25_data
            slide['status'] = 'draft'
            slide['last_modified'] = now
            slide['notes'] = (slide.get('notes', '') + ' | excel_p25')
        elif pn == 44:
            slide['template'] = 'split-image-text'
            slide['title'] = p44_data['title']
            slide['data'] = p44_data
            slide['status'] = 'draft'
            slide['last_modified'] = now
            slide['notes'] = (slide.get('notes', '') + ' | excel_p44')
        elif pn == 45:
            slide['template'] = 'split-image-text'
            slide['title'] = p45_data['title']
            slide['data'] = p45_data
            slide['status'] = 'draft'
            slide['last_modified'] = now
            slide['notes'] = (slide.get('notes', '') + ' | excel_p45')

    # 备份并写回
    backup = DECK_PATH.with_suffix('.yaml.excel.bak')
    if DECK_PATH.exists():
        import shutil
        shutil.copy2(DECK_PATH, backup)
        print(f'[OK] 旧 deck.yaml 备份到 {backup.name}')

    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(deck, f, allow_unicode=True, sort_keys=False,
                       width=100, default_flow_style=False)
    print(f'[OK] deck.yaml 已更新: p25/p44/p45 Excel 数据已回填')


def main():
    if not EXCEL_PATH.exists():
        print(f'[ERR] Excel 不存在: {EXCEL_PATH}', file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    print(f'sheets: {wb.sheetnames}')

    # 1. 设计方案 sheet
    ws_design = wb[SHEET_DESIGN]
    design_buildings = parse_building_table(ws_design)
    design_ind = parse_indicator_table(ws_design)
    print(f'\n[设计方案] 建筑单体 {len(design_buildings)} 行,综合指标 {len(design_ind)} 项')
    for b in design_buildings[:5]:
        print(' ', b)
    print(f'  用地面积={design_ind.get("用地面积", {}).get("val")}')
    print(f'  总建筑面积={design_ind.get("总建筑面积", {}).get("val")}')
    print(f'  容积率={design_ind.get("容积率", {}).get("val")}')
    print(f'  建筑密度={design_ind.get("建筑密度", {}).get("val")}')

    # 2. 二期规划 sheet
    ws_future = wb[SHEET_FUTURE]
    future_buildings = parse_building_table(ws_future)
    future_ind = parse_indicator_table(ws_future)
    print(f'\n[二期规划] 建筑单体 {len(future_buildings)} 行,综合指标 {len(future_ind)} 项')
    for b in future_buildings[:5]:
        print(' ', b)
    print(f'  用地面积={future_ind.get("用地面积", {}).get("val")}')
    print(f'  总建筑面积={future_ind.get("总建筑面积", {}).get("val")}')
    print(f'  容积率={future_ind.get("容积率", {}).get("val")}')

    # 3. 回填 deck.yaml
    print('\n[回填 deck.yaml]')
    update_deck(design_ind, design_buildings, future_ind, future_buildings)
    print('\n[下一步]')
    print('  跑 fill_content.py 填充其余文字内容')
    print('  跑 render_slide.py --all 渲染所有页')
    print('  跑 build_pdf.py 生成 PDF')


if __name__ == '__main__':
    main()
