"""
build_book.py - 图片+文字 → PDF 成果版 (轻量工具)

两种模式:
    1. 目录模式 (最简单): 丢图片进目录,自动按文件名排序生成
       python build_book.py --images ./效果图 --out 成果.pdf

    2. YAML 模式 (灵活): 写 pages.yaml 自定义每页标题/说明/布局
       python build_book.py --config pages.yaml --out 成果.pdf

依赖: pip install pyyaml playwright
      playwright install chromium

pages.yaml 格式:
    project: 安岳县柠檬冷链共享仓建设项目
    layout: 16:9          # 可选 16:9 / A4
    theme: warm           # warm 暖纸白 / dark 深色 / plain 纯白
    pages:
      - image: 鸟瞰1.png
        title: 鸟瞰效果图
        subtitle: 方案总览
        caption: 从东南方向俯瞰整个冷链园区
      - image: 透视1.png
        title: 透视图
        caption: 沿街立面效果
"""
import os
import sys
import re
import argparse
import yaml
from pathlib import Path

CANVAS = {'16:9': (1920, 1080), 'A4': (2480, 3508)}
THEMES = {
    'warm':  {'bg': '#F3F1ED', 'title': '#0E2A5B', 'sub': '#94A2B8', 'caption': '#4A5568'},
    'dark':  {'bg': '#1a1a1a', 'title': '#E2E8F0', 'sub': '#94A3B8', 'caption': '#CBD5E1'},
    'plain': {'bg': '#FFFFFF', 'title': '#1A202C', 'sub': '#718096', 'caption': '#4A5568'},
}


def natural_sort_key(s: str):
    """自然排序: 透视1, 透视2, 鸟瞰1, 鸟瞰2"""
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def load_from_dir(images_dir: Path) -> list:
    """从目录扫描图片,按文件名自然排序"""
    exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    files = [f for f in images_dir.iterdir() if f.suffix.lower() in exts]
    files.sort(key=lambda f: natural_sort_key(f.name))
    pages = []
    for f in files:
        pages.append({
            'image': str(f.resolve()),
            'title': f.stem,  # 文件名去扩展名作为标题
            'subtitle': '',
            'caption': '',
        })
    return pages


def load_from_yaml(config_path: Path) -> tuple:
    """从 YAML 加载页面配置,返回 (pages, project, layout, theme)"""
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    pages = cfg.get('pages', [])
    # 图片路径相对 config 文件所在目录解析
    base = config_path.parent
    for p in pages:
        img = p.get('image', '')
        if img and not Path(img).is_absolute():
            p['image'] = str((base / img).resolve())
    return pages, cfg.get('project', ''), cfg.get('layout', '16:9'), cfg.get('theme', 'warm')


def render_html(pages: list, project: str, layout: str, theme: str) -> str:
    """把页面列表渲染成完整 HTML"""
    W, H = CANVAS.get(layout, CANVAS['16:9'])
    t = THEMES.get(theme, THEMES['warm'])

    page_html = []
    for i, p in enumerate(pages):
        img = p.get('image', '')
        title = p.get('title', '')
        subtitle = p.get('subtitle', '')
        caption = p.get('caption', '')

        # 图片元素
        img_html = ''
        if img:
            img_html = f'<div class="image-box"><img src="{img}" alt=""></div>'
        else:
            img_html = '<div class="image-placeholder">图片位</div>'

        page_html.append(f'''
<div class="page" style="width:{W}px;height:{H}px;background:{t['bg']}">
  <div class="header">
    {f'<div class="project">{project}</div>' if project else ''}
    <div class="pagenum">{i+1}</div>
  </div>
  <div class="body">
    <div class="title-area">
      {f'<div class="title">{title}</div>' if title else ''}
      {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    {img_html}
    {f'<div class="caption">{caption}</div>' if caption else ''}
  </div>
</div>''')

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#333; }}
  .page {{
    position: relative;
    overflow: hidden;
    font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
    page-break-after: always;
  }}
  .page:last-child {{ page-break-after: auto; }}
  .header {{
    position: absolute; top: 0; left: 0; right: 0; height: 60px;
    display: flex; justify-content: space-between; align-items: center;
    padding: 0 50px;
  }}
  .project {{
    font-size: 22px; color: {t['title']}; letter-spacing: 4px;
    font-weight: 300;
  }}
  .pagenum {{
    font-size: 36px; color: {t['sub']}; font-family: Arial;
    font-weight: 200; opacity: 0.5;
  }}
  .body {{
    position: absolute; top: 80px; bottom: 60px; left: 50px; right: 50px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 24px;
  }}
  .title-area {{ text-align: center; margin-bottom: 8px; }}
  .title {{
    font-size: 52px; color: {t['title']}; font-weight: 700;
    letter-spacing: 6px; line-height: 1.2;
  }}
  .subtitle {{
    font-size: 26px; color: {t['sub']}; letter-spacing: 3px; margin-top: 8px;
  }}
  .image-box {{
    max-width: 100%; max-height: 72%;
    display: flex; align-items: center; justify-content: center;
  }}
  .image-box img {{
    max-width: 100%; max-height: 100%;
    object-fit: contain;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.15);
  }}
  .image-placeholder {{
    width: 60%; height: 50%;
    border: 3px dashed {t['sub']};
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    color: {t['sub']}; font-size: 32px; letter-spacing: 4px;
  }}
  .caption {{
    font-size: 22px; color: {t['caption']}; text-align: center;
    max-width: 90%; line-height: 1.6;
  }}
  @media print {{
    @page {{ size: {W}px {H}px; margin: 0; }}
    body {{ background: #fff; }}
    .page {{ page-break-after: always; }}
  }}
</style>
</head>
<body>
{''.join(page_html)}
</body>
</html>'''


def render_pdf(html: str, out_path: Path):
    """Playwright 渲染 HTML → PDF"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('[ERR] 未安装 playwright, 请: pip install playwright && playwright install chromium',
              file=sys.stderr)
        sys.exit(1)

    # 先写 HTML 调试文件
    debug = out_path.parent / 'deck.html'
    debug.write_text(html, encoding='utf-8')

    W, H = CANVAS.get('16:9', CANVAS['16:9'])  # 默认 16:9

    with sync_playwright() as p:
        # 优先用系统 Chrome, 没有则用 Playwright 自带 chromium
        try:
            browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': W, 'height': H})
        page.goto(debug.as_uri())
        page.pdf(
            path=str(out_path),
            width=f'{W}px',
            height=f'{H}px',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        browser.close()


def main():
    ap = argparse.ArgumentParser(description='图片+文字 → PDF 成果版')
    ap.add_argument('--images', default='', help='图片目录 (目录模式)')
    ap.add_argument('--config', default='', help='pages.yaml 路径 (YAML 模式)')
    ap.add_argument('--out', default='成果版.pdf', help='输出 PDF 路径')
    ap.add_argument('--project', default='', help='项目名 (页眉显示)')
    ap.add_argument('--layout', default='16:9', choices=['16:9', 'A4'])
    ap.add_argument('--theme', default='warm', choices=['warm', 'dark', 'plain'])
    args = ap.parse_args()

    if not args.images and not args.config:
        ap.error('必须提供 --images 或 --config 之一')

    # 加载页面配置
    if args.config:
        pages, project, layout, theme = load_from_yaml(Path(args.config))
        if args.project:
            project = args.project  # CLI 优先
        layout = args.layout
        theme = args.theme
    else:
        images_dir = Path(args.images)
        if not images_dir.is_dir():
            print(f'[ERR] 图片目录不存在: {images_dir}', file=sys.stderr)
            sys.exit(1)
        pages = load_from_dir(images_dir)
        project = args.project
        layout = args.layout
        theme = args.theme

    if not pages:
        print('[ERR] 没有找到任何页面配置', file=sys.stderr)
        sys.exit(1)

    print(f'[INFO] 共 {len(pages)} 页, 布局={layout}, 主题={theme}')

    # 渲染
    html = render_html(pages, project, layout, theme)
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_pdf(html, out_path)

    print(f'[OK] PDF 已生成: {out_path}')
    print(f'     大小: {out_path.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
