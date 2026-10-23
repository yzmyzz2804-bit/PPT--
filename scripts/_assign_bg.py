"""临时: 按章节语义把 bg_image 指向项目自有素材(非泛用),并渲染验证
API 恢复后跑 gen_bg.py 会自动覆盖回 AI 意向图"""
import re
import yaml
from pathlib import Path

DECK = Path(r'e:\TRAE\PPT概念规划设计\deck.yaml')
ASSIGN = {
    'cover': '../assets/images/renders/鸟瞰1.png',
    'ch1': '../assets/images/ref/p08.png',   # 卫星地块图
    'ch2': '../assets/images/ref/p06.png',   # 区位经济圈
    'ch3': '../assets/images/renders/透视2.png',  # 冷库立面意象
    'ch4': '../assets/images/ref/p20.png',   # 高清鸟瞰
    'ch5': '../assets/images/ref/p27.png',   # 功能分析
    'ch6': '../assets/images/ref/p46.png',   # 二期效果图
    'ch7': '../assets/images/ref/p49.png',   # 总平面图
}
deck = yaml.safe_load(DECK.read_text(encoding='utf-8'))
n = 0
for s in deck['slides']:
    key = 'cover' if s['template'] == 'cover' else (
        s.get('chapter') if s['template'] == 'chapter-divider' else None)
    if key and key in ASSIGN:
        s['data']['bg_image'] = ASSIGN[key]
        n += 1
DECK.write_text(yaml.safe_dump(deck, allow_unicode=True, sort_keys=False, width=200),
                encoding='utf-8')
print(f'bg_image 更新 {n} 页')
