"""
render_slide.py - 单页幻灯片渲染器

输入: deck.yaml 中的某个 slide 条目 + theme.json + templates/<template>.html
输出: slides/slide_NN.html (完整可独立浏览的 HTML 文档)

支持占位符替换：
    {{ var }}              - 简单变量
    {{#array}}...{{/array}} - 数组循环
    {{^exists}}...{{/exists}} - 反向条件

使用:
    python render_slide.py <slide_id>            # 渲染单页
    python render_slide.py --all                 # 渲染 deck.yaml 中所有页
"""
import re
import sys
import json
import argparse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
THEME_PATH = PROJECT_ROOT / 'theme.json'
TEMPLATES_DIR = PROJECT_ROOT / 'templates'
SLIDES_DIR = PROJECT_ROOT / 'slides'


class TemplateRenderer:
    """极简 mustache-like 模板引擎"""

    VAR_RE = re.compile(r'\{\{\s*([a-zA-Z0-9_.@]+)\s*\}\}')
    BLOCK_RE = re.compile(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', re.DOTALL)
    INV_BLOCK_RE = re.compile(r'\{\{\^(\w+)\}\}(.*?)\{\{/\1\}\}', re.DOTALL)

    def render(self, template: str, data: dict) -> str:
        # 1. 反向条件
        template = self._render_inv_blocks(template, data)
        # 2. 数组循环
        template = self._render_blocks(template, data)
        # 3. 简单变量
        template = self._render_vars(template, data)
        return template

    def _render_inv_blocks(self, tpl: str, data: dict) -> str:
        def repl(m):
            key = m.group(1)
            inner = m.group(2)
            val = data.get(key)
            if not val or (isinstance(val, list) and len(val) == 0):
                return self.render(inner, data)
            return ''
        return self.INV_BLOCK_RE.sub(repl, tpl)

    def _render_blocks(self, tpl: str, data: dict) -> str:
        def repl(m):
            key = m.group(1)
            inner = m.group(2)
            val = data.get(key)
            out = []
            if isinstance(val, list):
                for i, item in enumerate(val):
                    ctx = dict(data)  # 继承外层
                    if isinstance(item, dict):
                        ctx.update(item)
                    elif item is not None:
                        # 裸标量数组: {{ . }} 取当前项
                        ctx['.'] = str(item)
                    ctx['@index_1'] = str(i + 1)  # 1-based index
                    out.append(self.render(inner, ctx))
            elif val:
                # 标量条件块: 值为 truthy(非空字符串/数字)时渲染一次
                out.append(self.render(inner, data))
            return ''.join(out)
        return self.BLOCK_RE.sub(repl, tpl)

    def _render_vars(self, tpl: str, data: dict) -> str:
        def repl(m):
            key = m.group(1)
            if key == '.':
                return str(data.get('.', ''))
            # 支持点路径 + 数组索引 (headers.0)
            parts = key.split('.')
            val = data
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, '')
                elif isinstance(val, list) and p.isdigit() and int(p) < len(val):
                    val = val[int(p)]
                else:
                    val = ''
                    break
            if val is None:
                return ''
            return str(val)
        return self.VAR_RE.sub(repl, tpl)


# 图片类字段(命中即做文件体检)
_IMG_KEYS = {'image', 'bg_image', 'icon', 'cover', 'photo', 'avatar', 'logo', 'thumb'}
_IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')


def _is_blank_image(path: Path) -> bool:
    """近纯白图(失败的抽图)视为空白。PIL 为可选依赖,缺失则跳过内容检测"""
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(path) as im:
            w, h = im.size
            if w < 200 or h < 150:
                return True
            small = im.convert('RGB').resize((128, 72))
            px = list(small.getdata())
            white = sum(1 for r, g, b in px if min(r, g, b) > 242) / len(px)
            return white > 0.985
    except Exception:
        return False


def null_missing_images(obj, project_root: Path):
    """递归: 指向"不存在/近空白"文件的本地图片路径置 '',交给模板渲染占位相框。
    slides/*.html 中 '../assets/x' 实际相对项目根,故剥掉首层 ../ 解析。"""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if (isinstance(v, str) and v.startswith('../')
                    and v.lower().endswith(_IMG_EXTS)
                    and (k in _IMG_KEYS or 'image' in k)):
                p = project_root / v[3:]
                if not p.exists() or _is_blank_image(p):
                    obj[k] = ''
            else:
                null_missing_images(v, project_root)
    elif isinstance(obj, list):
        for it in obj:
            null_missing_images(it, project_root)


def load_theme_vars(theme_path: Path) -> str:
    """从 theme.json 生成 :root CSS 变量声明"""
    with open(theme_path, 'r', encoding='utf-8') as f:
        theme = json.load(f)

    lines = ['    /* —— theme.json 自动注入 (勿手动改) —— */']
    colors = theme.get('colors', {})
    for group, items in colors.items():
        for name, val in items.items():
            var_name = f'--{"brand" if group == "brand" else "c"}-{name}' if group != 'brand' else f'--brand-{name}'
            if group == 'brand':
                var_name = f'--brand-{name}'
            elif group == 'neutral':
                var_name = f'--c-{name}'
            else:
                var_name = f'--c-{group}_{name}'
            lines.append(f'    {var_name}: {val};')

    typo = theme.get('typography', {})
    fonts = typo.get('font_cn', '')
    lines.append(f'    --font-cn: {fonts};')
    lines.append(f'    --font-en: {typo.get("font_en", "")};')
    lines.append(f'    --font-num: {typo.get("font_num", "")};')

    scale = typo.get('scale', {})
    for k, v in scale.items():
        lines.append(f'    --fs-{k.replace("page_", "")}: {v};')

    layout = theme.get('layout', {})
    lines.append(f'    --slide-w: {layout.get("canvas_w", "1920px")};')
    lines.append(f'    --slide-h: {layout.get("canvas_h", "1080px")};')
    lines.append(f'    --safe-margin: {layout.get("safe_margin", "80px")};')

    return '\n'.join(lines)


def inject_theme_vars(template_html: str, theme_vars_css: str) -> str:
    """把 theme 变量注入到模板 <style> 块顶部"""
    # 在第一个 <style> 之后插入 :root 块
    style_pos = template_html.find('<style>')
    if style_pos == -1:
        return template_html  # 模板没有 style 块,跳过
    insert_at = style_pos + len('<style>')
    root_block = f"\n:root {{\n{theme_vars_css}\n}}\n"
    return template_html[:insert_at] + root_block + template_html[insert_at:]


def load_chapter_colors(theme_path: Path) -> dict:
    """读取分章强调色表 {ch1: '#...', ...}"""
    with open(theme_path, 'r', encoding='utf-8') as f:
        theme = json.load(f)
    return {k: v for k, v in theme.get('chapter_colors', {}).items()
            if not k.startswith('_')}


def render_one(slide: dict, deck: dict, theme_vars_css: str,
               chapter_colors: dict | None = None) -> str:
    """渲染单页"""
    template_name = slide.get('template', 'split-image-text')
    template_path = TEMPLATES_DIR / f'{template_name}.html'
    if not template_path.exists():
        raise FileNotFoundError(f'模板不存在: {template_path}')

    template_html = template_path.read_text(encoding='utf-8')

    # 剥离模板顶部的 HTML 注释元数据
    template_html = re.sub(r'^<!--.*?-->\s*', '', template_html, flags=re.DOTALL)

    # 准备渲染数据: 全局 deck 上下文 + 单页 data
    chapter = slide.get('chapter', '') or ''
    render_data = {
        'project_name': deck.get('project', {}).get('name', ''),
        'project_name_en': deck.get('project', {}).get('name_en', ''),
        'date': deck.get('project', {}).get('date', ''),
        'page_num': slide.get('page_num', ''),
        'total_pages': deck.get('_total_pages', len(deck.get('slides', []))),
        'chapter': chapter,
    }
    if isinstance(slide.get('data'), dict):
        render_data.update(slide['data'])

    # 图片体检: 缺失/近空白的本地图置空,模板统一渲染占位相框
    null_missing_images(render_data, PROJECT_ROOT)

    # 渲染占位符
    renderer = TemplateRenderer()
    rendered = renderer.render(template_html, render_data)

    # 分章强调色: 按 slide.chapter 注入 --ch-accent(无章节则回退主色)
    ch_color = (chapter_colors or {}).get(chapter)
    ch_css = f'    --ch-accent: {ch_color};' if ch_color \
        else '    --ch-accent: var(--brand-primary);'
    slide_theme_vars = theme_vars_css + '\n' + ch_css

    # 注入主题变量
    rendered = inject_theme_vars(rendered, slide_theme_vars)

    # 修复 base.css 引用路径（slides/NN.html 引用 ../base.css）
    # 模板里是 ../base.css，slides/ 在根，所以从 slides/NN.html 看 ../base.css 正确
    return rendered


def render_slide_by_id(slide_id: str):
    if not DECK_PATH.exists():
        print(f'✗ deck.yaml 不存在: {DECK_PATH}')
        sys.exit(1)
    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    slides = deck.get('slides', [])
    target = next((s for s in slides if s['id'] == slide_id), None)
    if target is None:
        print(f'✗ 找不到 slide_id={slide_id}, 当前 deck 有: {[s["id"] for s in slides]}')
        sys.exit(1)

    theme_vars = load_theme_vars(THEME_PATH)
    chapter_colors = load_chapter_colors(THEME_PATH)
    html = render_one(target, deck, theme_vars, chapter_colors)

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SLIDES_DIR / f'{slide_id}.html'
    out_path.write_text(html, encoding='utf-8')

    # 更新 deck.yaml 状态
    target['status'] = 'rendered'
    from datetime import datetime
    target['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f'✓ 渲染完成: {out_path}')


def render_all():
    if not DECK_PATH.exists():
        print(f'✗ deck.yaml 不存在')
        sys.exit(1)
    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)
    slides = deck.get('slides', [])
    deck['_total_pages'] = len(slides)
    theme_vars = load_theme_vars(THEME_PATH)
    chapter_colors = load_chapter_colors(THEME_PATH)
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    for s in slides:
        # locked 页跳过,强制保留
        if s.get('status') == 'locked':
            print(f'  ⊘ 跳过 locked 页: {s["id"]}')
            continue
        s['page_num'] = str(slides.index(s) + 1)
        html = render_one(s, deck, theme_vars, chapter_colors)
        out_path = SLIDES_DIR / f'{s["id"]}.html'
        out_path.write_text(html, encoding='utf-8')
        s['status'] = 'rendered'
        s['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        print(f'  ✓ {s["id"]}: {out_path}')
    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f'✓ 全部渲染完成: {len(slides)} 页')


def main():
    ap = argparse.ArgumentParser(description='渲染单页幻灯片')
    ap.add_argument('slide_id', nargs='?', help='要渲染的 slide_id,如 slide_01')
    ap.add_argument('--all', action='store_true', help='渲染 deck.yaml 中所有页')
    args = ap.parse_args()
    if args.all:
        render_all()
    elif args.slide_id:
        render_slide_by_id(args.slide_id)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
