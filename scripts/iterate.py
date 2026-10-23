"""
iterate.py - 迭代入口 (用户改 PPT 的统一入口)

子命令:
    list                     列出所有页 + 状态
    render <slide_id>        仅重渲染指定页 (其他页 0 改动)
    render --all             重渲染所有非 locked 页
    add <template> <chapter> 新增一页(默认 draft 状态,需后续填数据)
    remove <slide_id>        从 deck 移除一页
    lock <slide_id>          锁定某页(强制保留,不参与重渲染)
    unlock <slide_id>        解锁
    edit <slide_id>          在默认编辑器打开 slides/<id>.html
    build                    构建 PDF (调用 build_pdf.py)
    build --pptx             构建 PPTX
    status                   显示项目状态摘要

使用示例:
    python iterate.py list
    python iterate.py render slide_05     # 改完 slide_05 后只重渲染这一页
    python iterate.py build               # 重组 PDF
"""
import sys
import argparse
import yaml
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DECK_PATH = PROJECT_ROOT / 'deck.yaml'
SCRIPTS_DIR = Path(__file__).parent


def load_deck() -> dict:
    if not DECK_PATH.exists():
        print(f'✗ deck.yaml 不存在,请先运行 parse_coze_md.py')
        sys.exit(1)
    with open(DECK_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_deck(deck: dict):
    with open(DECK_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(deck, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def cmd_list(args):
    deck = load_deck()
    slides = deck.get('slides', [])
    if not slides:
        print('(空) deck.yaml 中没有 slides。先用 parse_coze_md.py 解析 COZE MD 草稿。')
        return
    print(f'项目: {deck.get("project", {}).get("name", "")} | 主题: {deck.get("theme", "")}')
    print(f'共 {len(slides)} 页:')
    print(f'  {"ID":<12} {"章节":<8} {"版式":<26} {"状态":<10} {"标题"}')
    print(f'  {"-"*12} {"-"*8} {"-"*26} {"-"*10} {"-"*30}')
    for s in slides:
        print(f'  {s["id"]:<12} {s.get("chapter",""):<8} {s.get("template",""):<26} '
              f'{s.get("status",""):<10} {s.get("title","")}')


def cmd_render(args):
    cmd = [sys.executable, str(SCRIPTS_DIR / 'render_slide.py')]
    if args.slide_id == 'all' or args.slide_id is None and args.all:
        cmd.append('--all')
    else:
        cmd.append(args.slide_id)
    subprocess.run(cmd, check=True)


def cmd_add(args):
    deck = load_deck()
    slides = deck.get('slides', [])
    # 找到该 chapter 的最后一页,在其后插入;否则追加到末尾
    new_id = f'slide_{len(slides) + 1:02d}'
    # 检查 template 存在
    tpl_path = PROJECT_ROOT / 'templates' / f'{args.template}.html'
    if not tpl_path.exists():
        print(f'✗ 模板不存在: {tpl_path}')
        print(f'  可用模板: {[p.stem for p in (PROJECT_ROOT / "templates").glob("*.html")]}')
        sys.exit(1)
    new_slide = {
        'id': new_id,
        'chapter': args.chapter,
        'template': args.template,
        'title': f'新页 ({args.template})',
        'status': 'draft',
        'assets': [],
        'last_modified': '',
        'notes': '由 iterate.py add 创建,待填充 data',
        'data': {},
    }
    # 找插入位置
    insert_at = len(slides)
    for i, s in enumerate(slides):
        if s.get('chapter') == args.chapter:
            insert_at = i + 1
    slides.insert(insert_at, new_slide)
    deck['slides'] = slides
    save_deck(deck)
    print(f'✓ 已新增: {new_id} (chapter={args.chapter}, template={args.template})')
    print(f'  下一步: 编辑 deck.yaml 中该页的 data,然后 python iterate.py render {new_id}')


def cmd_remove(args):
    deck = load_deck()
    slides = deck.get('slides', [])
    target = next((s for s in slides if s['id'] == args.slide_id), None)
    if target is None:
        print(f'✗ 找不到: {args.slide_id}')
        sys.exit(1)
    if target.get('status') == 'locked':
        print(f'✗ {args.slide_id} 已 locked,先 unlock 再 remove')
        sys.exit(1)
    slides = [s for s in slides if s['id'] != args.slide_id]
    deck['slides'] = slides
    save_deck(deck)
    # 删除对应 HTML
    slide_html = PROJECT_ROOT / 'slides' / f'{args.slide_id}.html'
    if slide_html.exists():
        slide_html.unlink()
    print(f'✓ 已移除: {args.slide_id}')


def cmd_lock(args):
    deck = load_deck()
    for s in deck.get('slides', []):
        if s['id'] == args.slide_id:
            s['status'] = 'locked'
            save_deck(deck)
            print(f'✓ 已锁定: {args.slide_id} (后续 render --all 会跳过此页)')
            return
    print(f'✗ 找不到: {args.slide_id}')


def cmd_unlock(args):
    deck = load_deck()
    for s in deck.get('slides', []):
        if s['id'] == args.slide_id:
            s['status'] = 'draft'
            save_deck(deck)
            print(f'✓ 已解锁: {args.slide_id}')
            return
    print(f'✗ 找不到: {args.slide_id}')


def cmd_build(args):
    if args.pptx:
        cmd = [sys.executable, str(SCRIPTS_DIR / 'build_pptx.py')]
    else:
        cmd = [sys.executable, str(SCRIPTS_DIR / 'build_pdf.py')]
    subprocess.run(cmd, check=True)


def cmd_status(args):
    deck = load_deck()
    project = deck.get('project', {})
    slides = deck.get('slides', [])
    by_status = {}
    for s in slides:
        st = s.get('status', 'unknown')
        by_status[st] = by_status.get(st, 0) + 1
    print('=== 项目状态 ===')
    print(f'  名称: {project.get("name","")}')
    print(f'  类型: {project.get("type","")}')
    print(f'  主题: {deck.get("theme","")}')
    print(f'  调性: {project.get("tone","")}')
    print(f'  概念词: {deck.get("concept", {}).get("theme_words", [])}')
    print(f'  页面总数: {len(slides)}')
    print(f'  状态分布: {by_status}')
    build = deck.get('build', {})
    if build.get('last_build'):
        print(f'  最近构建: {build.get("last_build","")} → {build.get("last_build_pdf","") or build.get("last_build_pptx","")}')


def main():
    ap = argparse.ArgumentParser(
        description='PPT 迭代入口 - 增量改 N 页只重渲染 slide_N,其他页 0 改动',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n  python iterate.py list\n  python iterate.py render slide_05\n  python iterate.py build'
    )
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list', help='列出所有页').set_defaults(func=cmd_list)
    sub.add_parser('status', help='项目状态摘要').set_defaults(func=cmd_status)

    p_render = sub.add_parser('render', help='渲染页面')
    p_render.add_argument('slide_id', nargs='?', help='slide_id 或 "all"')
    p_render.add_argument('--all', action='store_true', help='渲染所有非 locked 页')
    p_render.set_defaults(func=cmd_render)

    p_add = sub.add_parser('add', help='新增一页')
    p_add.add_argument('template', help='模板名(不含扩展名),如 quadrant-2x2')
    p_add.add_argument('chapter', help='章节 id,如 ch3')
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser('remove', help='移除一页')
    p_rm.add_argument('slide_id')
    p_rm.set_defaults(func=cmd_remove)

    p_lock = sub.add_parser('lock', help='锁定某页(强制保留)')
    p_lock.add_argument('slide_id')
    p_lock.set_defaults(func=cmd_lock)

    p_unlock = sub.add_parser('unlock', help='解锁')
    p_unlock.add_argument('slide_id')
    p_unlock.set_defaults(func=cmd_unlock)

    p_build = sub.add_parser('build', help='构建 PDF 或 PPTX')
    p_build.add_argument('--pptx', action='store_true', help='构建 PPTX 而非 PDF')
    p_build.set_defaults(func=cmd_build)

    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
