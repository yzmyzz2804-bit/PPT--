"""
gen_bg.py - 意向图智能生成 + 封面/章节/结尾页默认数据回填

v2: 文本分析驱动 —— 不再写死关键词
  1. analyze_deck(): 读 deck.yaml 全部文本(项目名/类型/主题词/章节名/章节内容/页标题)
     → 识别项目类型(冷链/鞋服/物流/产业园/住宅/商业) → 选定封面意象场景
  2. 每个章节按章节名模糊匹配专属意象(场地→鸟瞰场地 / 市场→城市语境 /
     概念→抽象体量 / 方案→建筑渲染 / 分析→流线抽象 / 二期→地平线远景 /
     图纸→蓝图肌理 / 说明→材质细节),每章生成独立 divider_chN.jpg
  3. 生成 → assets/images/bg/ ,并把 bg_image 回写 deck.yaml 对应页

使用:
    python gen_bg.py                       # 分析+生成封面+每章分隔图+回填
    python gen_bg.py --only cover          # 只生成封面
    python gen_bg.py --skip-gen --fill     # 跳过生成,只回填数据

用户有实景图时: 直接覆盖 assets/images/bg/ 同名文件,再 --skip-gen --fill。
COZE 沙箱无图像 API: main.py --skip-bg-gen 跳过本脚本。
"""
import re
import sys
import time
import argparse
import urllib.request
import urllib.parse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
BG_DIR = PROJECT_ROOT / 'assets' / 'images' / 'bg'

API = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'

# ================================================================
# 意象库: 项目类型 → 封面场景 (按命中关键词优先级排列)
# ================================================================
TYPE_SCENES = [
    ('cold_chain', '冷链 冷库 冷藏 冷冻 仓储 冷链物流 保鲜 冷链共享',
     'vast cold storage warehouse exterior, blue-grey metal facades, refrigerated '
     'dock with faint frost mist, cooling units on roof, cool dawn light'),
    ('garment', '鞋服 鞋业 制鞋 服装 针纺 服饰',
     'modern garment factory campus, clean production workshops, textile material '
     'textures, warm workshop light through clerestory windows'),
    ('logistics', '物流 快递 供应链 枢纽 分拨 集散',
     'logistics distribution center, orderly container yard, loading docks in '
     'rhythm, dusk sky with moving light trails'),
    ('residential', '住宅 社区 人居 安居 康养 宜居',
     'modern residential community, layered courtyards, greenery between '
     'buildings, evening warm light on facades'),
    ('commercial', '商业 办公 城市客厅 综合体 科创',
     'urban commercial complex, glass curtain walls, vibrant street frontage, '
     'city avenue perspective'),
    ('industrial', '产业园 工业园 制造 厂房 加工 生产 共享仓',
     'modern industrial park, clean factory clusters, landscaped campus road, '
     'morning haze over rooftops'),
]
DEFAULT_SCENE = ('modern architecture complex, clean facade rhythm, '
                 'atmospheric sky, architectural concept design')

# ================================================================
# 意象库: 章节名关键词 → 分隔页场景 (模糊匹配,首个命中生效)
# ================================================================
CHAPTER_SCENES = [
    ('场地|区位|研判', 'aerial view of site and surroundings, road context, '
     'gentle topography, soft morning daylight'),
    ('市场|产业|洞察|依据', 'city context skyline, dense urban texture, '
     'economic corridor at dusk'),
    ('概念|主旨|主题|理念', 'abstract white massing model, light and shadow on '
     'pure geometry, minimal composition'),
    ('方案|呈现|效果', 'photorealistic architectural rendering of building '
     'complex, dramatic clouds, hero perspective'),
    ('分析|流线|功能', 'abstract spatial diagram, flowing light lines through '
     'building volume, dark minimal background'),
    ('二期|远期|未来|拓展', 'future expansion horizon, phased growth field, '
     'hopeful dawn light over open land'),
    ('图纸|平面|立面|剖', 'blueprint texture, precise technical drawing lines, '
     'white model resting on draft paper'),
    ('说明|策略|实施', 'facade material detail close-up, craftsmanship texture, '
     'raking light on surface'),
]
CHAPTER_DEFAULT = 'architectural atmosphere, facade rhythm, sky and shadow'

# 固定品质词(所有 prompt 共用)
STYLE_TAIL = ('architectural concept design presentation, cinematic wide shot, '
              'soft haze, muted professional color palette, photorealistic, '
              'high detail, no text, no watermark')


def analyze_deck(deck: dict) -> dict:
    """读全部文本 → {cover_prompt, chapter_prompts: {ch_id: prompt}, theme_words}"""
    project = deck.get('project', {})
    concept = deck.get('concept', {})
    theme_words = concept.get('theme_words', [])

    # 汇总项目级文本
    corpus_parts = [project.get('name', ''), project.get('type', ''),
                    ' '.join(theme_words), concept.get('core_logic', '')]
    for c in concept.get('chapters', []):
        corpus_parts += [c.get('word', ''), c.get('problem', ''), c.get('content', '')]
    corpus = ' '.join(p for p in corpus_parts if p)

    # 1. 项目类型 → 封面场景
    cover_scene = DEFAULT_SCENE
    for _tid, keywords, scene in TYPE_SCENES:
        if any(k in corpus for k in keywords.split()):
            cover_scene = scene
            break
    cover_prompt = f'{cover_scene}, {STYLE_TAIL}'

    # 2. 每章 → 分隔页场景
    chapter_prompts = {}
    for c in deck.get('narrative_chapters', []):
        name = c.get('name', '')
        scene = CHAPTER_DEFAULT
        for pat, ch_scene in CHAPTER_SCENES:
            if re.search(pat, name):
                scene = ch_scene
                break
        chapter_prompts[c['id']] = f'{scene}, {STYLE_TAIL}'

    # 章节名也出现在 slides 标题但 narrative_chapters 缺失时,兜底扫 chapter-divider
    for s in deck.get('slides', []):
        if s.get('template') != 'chapter-divider' or s.get('chapter') in chapter_prompts:
            continue
        title = s.get('title', '')
        scene = CHAPTER_DEFAULT
        for pat, ch_scene in CHAPTER_SCENES:
            if re.search(pat, title):
                scene = ch_scene
                break
        chapter_prompts[s['chapter']] = f'{scene}, {STYLE_TAIL}'

    return {'cover_prompt': cover_prompt, 'chapter_prompts': chapter_prompts,
            'theme_words': theme_words, 'cover_scene': cover_scene}


# ================================================================
# 图像生成 (异步 API 轮询)
# ================================================================
def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def gen_image(prompt: str, out_path: Path):
    """异步 API: 首次请求返回占位图,轮询直到内容发生跃变(占位→成品)。

    注意: 不能用"两次相同"判断完成——生成期间占位图恒定相同,会在
    未完成时就误保存占位图(表现为多张 prompt 不同的图 hash 一致)。
    """
    prompt_q = urllib.parse.quote(prompt)
    url = f'{API}?prompt={prompt_q}&image_size=landscape_16_9'
    print(f'  生成 {out_path.name} (轮询中) ...', flush=True)
    first = _fetch(url)
    for i in range(30):  # 最多 ~150s
        time.sleep(5)
        cur = _fetch(url)
        if cur != first:  # 内容跃变 → 成品就绪
            out_path.write_bytes(cur)
            print(f'  ✓ {out_path.name} ({len(cur)//1024} KB, 跃变@轮询{i+1})',
                  flush=True)
            return
        first = cur
    out_path.write_bytes(first)
    print(f'  ⚠ {out_path.name} 未见跃变(可能缓存命中即成品),保存最后帧 '
          f'({len(first)//1024} KB)', flush=True)


# ================================================================
# 回填 deck.yaml
# ================================================================
def fill_defaults(deck: dict, generated: dict):
    """回填 cover/chapter-divider/closing 缺失字段 + 写入意向图路径"""
    project = deck.get('project', {})
    theme_words = deck.get('concept', {}).get('theme_words', [])
    slogan = '·'.join(theme_words) if theme_words else project.get('name', '')
    chapters = {c['id']: c for c in deck.get('narrative_chapters', [])}
    concept_ch = {c.get('word'): c for c in deck.get('concept', {}).get('chapters', [])}

    for s in deck.get('slides', []):
        tpl = s.get('template', '')
        data = s.setdefault('data', {})

        if tpl == 'cover':
            # 封面意向图(本次生成的一定写入,覆盖旧默认)
            data['bg_image'] = '../assets/images/bg/cover.jpg'
            if data.get('title', '') in ('封面', ''):
                data['title'] = slogan
            data.setdefault('subtitle', '')
            data.setdefault('project_name', project.get('name', ''))

        elif tpl == 'chapter-divider':
            ch_id = s.get('chapter', '')
            # 每章专属意向图
            if ch_id in generated['chapter_files']:
                data['bg_image'] = f'../assets/images/bg/{generated["chapter_files"][ch_id]}'
            else:
                data.setdefault('bg_image', '../assets/images/bg/divider.jpg')
            m = re.search(r'(\d+)', s.get('title', ''))
            if m:
                data.setdefault('chapter_num', m.group(1).zfill(2))
            elif ch_id in chapters:
                data.setdefault('chapter_num', re.sub(r'\D', '', ch_id).zfill(2))
            if data.get('chapter_name') in (None, ''):
                data['chapter_name'] = re.sub(r'^[0-9\s]+', '', s.get('title', ''))
            data['chapter_name'] = re.sub(r'^[0-9\s]+', '', data.get('chapter_name', ''))
            ch_name = data.get('chapter_name', '')
            for c in chapters.values():
                if c['name'] == ch_name and c.get('name_en'):
                    data.setdefault('chapter_name_en', c['name_en'])
                    break
            if ch_name in concept_ch and concept_ch[ch_name].get('problem'):
                data.setdefault('chapter_desc', concept_ch[ch_name]['problem'])
            data.setdefault('chapter_name_en', '')
            data.setdefault('chapter_desc', '')

        elif tpl == 'closing':
            data.setdefault('closing_text', slogan)
            data.setdefault('closing_sub', 'THANKS')
            data.setdefault('project_name', project.get('name', ''))


def main():
    ap = argparse.ArgumentParser(description='意向图智能生成 + 回填 deck 默认数据')
    ap.add_argument('--only', choices=['cover', 'divider'], help='只生成指定类型')
    ap.add_argument('--skip-gen', action='store_true', help='跳过图像生成')
    args = ap.parse_args()

    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    # 1. 文本分析
    plan = analyze_deck(deck)
    print(f'✓ 项目类型意象: {plan["cover_scene"][:60]}...')
    print(f'✓ 章节意向图: {len(plan["chapter_prompts"])} 张')

    generated = {'chapter_files': {}}

    # --skip-gen 时扫描已有章节意向图,照常回填路径
    if args.skip_gen and BG_DIR.exists():
        for f in BG_DIR.glob('divider_ch*.jpg'):
            m = re.search(r'ch(\d+)', f.name)
            if m:
                generated['chapter_files'][f'ch{int(m.group(1))}'] = f.name

    # 2. 生成
    if not args.skip_gen:
        BG_DIR.mkdir(parents=True, exist_ok=True)
        if args.only in (None, 'cover'):
            out = BG_DIR / 'cover.jpg'
            if out.exists():
                print(f'  ⊘ 已存在,跳过: {out.name} (覆盖请先删除)')
            else:
                gen_image(plan['cover_prompt'], out)
        if args.only in (None, 'divider'):
            for ch_id, prompt in plan['chapter_prompts'].items():
                num = re.sub(r'\D', '', ch_id).zfill(2) or '00'
                fname = f'divider_ch{num}.jpg'
                out = BG_DIR / fname
                generated['chapter_files'][ch_id] = fname
                if out.exists():
                    print(f'  ⊘ 已存在,跳过: {fname} (覆盖请先删除)')
                    continue
                gen_image(prompt, out)

    # 3. 回填
    fill_defaults(deck, generated)
    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print('✓ deck.yaml 已回填(意向图路径+默认数据)')


if __name__ == '__main__':
    main()
