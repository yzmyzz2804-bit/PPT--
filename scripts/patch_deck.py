"""
patch_deck.py - 修复三个问题:
  1. scheme-num 打架 → p20-23/46/47 清空 scheme_num,让模板条件块自然隐藏
  2. 指标不要远期拓展 → p25 清空 summary_cards
  3. cover 缺主题词 → p1 cover 加 subtitle='鲜藏·共享·链通'
"""
import yaml, shutil
from pathlib import Path
from datetime import datetime

DECK = Path(r'e:\TRAE\PPT概念规划设计\deck.yaml')
bak = DECK.with_suffix('.yaml.patch.bak')
shutil.copy2(DECK, bak); print(f'备份: {bak.name}')

with open(DECK, 'r', encoding='utf-8') as f:
    deck = yaml.safe_load(f)

now = datetime.now().strftime('%Y-%m-%d %H:%M')

for s in deck['slides']:
    pn = s['page_num']
    d = s['data']
    # (3) cover 加主题词
    if pn == '1' and s['template'] == 'cover':
        d.setdefault('subtitle', '鲜藏·共享·链通')
        s['last_modified'] = now
        print(f'[cover] p1 加 subtitle={d["subtitle"]!r}')
    # (1) scheme-present 效果图页: 清空 scheme_num 让模板隐藏 SCHEME 编号
    if pn in ('20','21','22','23','46','47') and s['template'] == 'scheme-present':
        d['scheme_num'] = ''
        s['last_modified'] = now
        print(f'[scheme] p{pn} 清空 scheme_num')
    # (2) p25 清空 summary_cards (不要远期拓展)
    if pn == '25' and s['template'] == 'compare-table':
        d['summary_cards'] = []
        s['last_modified'] = now
        print(f'[summary] p25 清空 summary_cards')
    # p44/45 二期规划文字简化为规划建议口吻
    if pn in ('44','45') and s['template'] == 'split-image-text':
        for c in d.get('cards', []):
            if '指标' in c.get('title','') or '指标' in c.get('text',''):
                # 把含具体数字的指标段落简化
                c['text'] = '二期规划为远期土地供应后的拓展倡议。本期仅作规划可行性分析，不与设计方案做经济指标对比。'
                print(f'[future] p{pn} 简化指标文字')

with open(DECK, 'w', encoding='utf-8') as f:
    yaml.safe_dump(deck, f, allow_unicode=True, sort_keys=False, width=100, default_flow_style=False)
print(f'[OK] patch 完成: {DECK}')
