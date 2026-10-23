"""
main.py - PPT 概念方案生成引擎 · 统一 CLI 入口

形态 A 打包版: 单文件 ZIP,一条命令出 PDF

三种使用模式:
    1) 全流程 (COZE agent 推荐):
       python main.py build \
           --name "安岳县柠檬冷链共享仓建设项目" \
           --ref-pdf <参考PDF> \
           --project-type industrial_park \
           --excel <指标表.xlsx> \
           --renders <效果图目录> \
           --skip-bg-gen

    2) 迭代 (已有项目):
       python main.py re-render --project <项目目录> --slides 20,22,25
       python main.py rebuild --project <项目目录>

    3) 单独步骤 (开发调试):
       python main.py parse-pdf --ref-pdf <参考.pdf> --out <项目目录>
       python main.py parse-excel --project <项目目录> --excel <指标.xlsx>
       python main.py render --project <项目目录>
       python main.py pdf --project <项目目录> --out xxx.pdf

所有脚本都通过 PPT_ENGINE_ROOT / PPT_PROJECT 环境变量感知路径,
main.py 自动设置这两个环境变量后再调用,无需手改脚本。
"""
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# —— 引擎根 = main.py 所在目录 ——
ENGINE_ROOT = Path(__file__).resolve().parent

def run(script: str, project_root: Path, *extra_args: str, capture: bool = False) -> int:
    """在 PPT_PROJECT/PPT_ENGINE_ROOT 环境下运行 scripts/*.py"""
    env = os.environ.copy()
    env['PPT_ENGINE_ROOT'] = str(ENGINE_ROOT)
    env['PPT_PROJECT'] = str(project_root)

    cmd = [
        sys.executable,
        str(ENGINE_ROOT / 'scripts' / script),
        *extra_args,
    ]
    print(f'  $ python {script} {" ".join(extra_args)}')
    try:
        if capture:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout.strip())
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
            return result.returncode
        else:
            return subprocess.call(cmd, env=env)
    except Exception as e:
        print(f'  ✗ 执行失败: {e}', file=sys.stderr)
        return 1


def ensure_project_dir(project_root: Path):
    """确保项目目录骨架存在"""
    project_root.mkdir(parents=True, exist_ok=True)
    for sub in ['slides', 'build', 'assets', 'assets/images', 'assets/images/renders',
                'assets/images/bg']:
        (project_root / sub).mkdir(parents=True, exist_ok=True)


def copy_renders(src_dir: Path, project_root: Path):
    """复制效果图到项目目录的 assets/images/renders/"""
    dst = project_root / 'assets' / 'images' / 'renders'
    if not src_dir.exists():
        print(f'  ⚠ 效果图目录不存在: {src_dir}')
        return
    count = 0
    for f in src_dir.iterdir():
        if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            shutil.copy2(f, dst / f.name)
            count += 1
    print(f'  ✓ 复制效果图 {count} 张 → {dst}')


# ================================================================
# subcommand: build
# ================================================================
def cmd_build(args):
    """全流程: 从素材到 PDF 一把出"""
    # 1. 创建项目目录
    name = args.name or 'ppt_project'
    safe_name = name.replace('/', '_').replace('\\', '_')
    project_root = Path(args.project) if args.project else (
        ENGINE_ROOT / 'workdir' / safe_name
    )
    ensure_project_dir(project_root)
    print(f'\n📂 项目目录: {project_root}')

    # 2. 复制效果图
    if args.renders:
        copy_renders(Path(args.renders), project_root)

    # 3. parse_v2_pdf → deck.yaml
    if args.ref_pdf:
        print(f'\n🔍 [1/5] 解析参考 PDF → deck.yaml')
        rc = run('parse_v2_pdf.py', project_root)
        if rc != 0:
            print('  ✗ parse_v2_pdf.py 失败', file=sys.stderr)
            return 1
        # 3b. fill_from_ref_pdf → 每页文字+分析图回填 (成果版关键)
        print(f'\n🖼 [1b/5] 参考 PDF 文字+分析图回填')
        rc = run('fill_from_ref_pdf.py', project_root, args.ref_pdf)
        if rc != 0:
            print('  ⚠ fill_from_ref_pdf.py 失败,继续(骨架仍有章节内容点)', file=sys.stderr)
    else:
        print(f'\n⚠ 未提供 --ref-pdf,跳过 parse_v2_pdf')

    # 4. parse_coze_md (可选)
    if args.md:
        print(f'\n📝 [2/5] 解析 COZE MD → 回填 deck.yaml')
        rc = run('parse_coze_md.py', project_root, args.md,
                 '--project-type', args.project_type or 'industrial_park')
        if rc != 0:
            print('  ✗ parse_coze_md.py 失败', file=sys.stderr)
            return 1

    # 5. parse_excel (可选)
    if args.excel:
        print(f'\n📊 [3/5] 解析 Excel 指标 → 回填 deck.yaml')
        rc = run('parse_excel.py', project_root)
        if rc != 0:
            print('  ✗ parse_excel.py 失败', file=sys.stderr)
            return 1
    else:
        print(f'\n⚠ 未提供 --excel,跳过 parse_excel')

    # 6. fill_content
    print(f'\n🖊 [4/5] 填充内容')
    rc = run('fill_content.py', project_root)
    if rc != 0:
        print('  ⚠ fill_content.py 返回非零,继续')

    # 7. gen_bg (可选)
    if not args.skip_bg_gen:
        print(f'\n🎨 [4.5/5] 生成底图')
        rc = run('gen_bg.py', project_root)
        if rc != 0:
            print('  ⚠ gen_bg.py 失败,继续')
    else:
        print(f'\n⏭ 跳过底图生成 (--skip-bg-gen)')

    # 8. render_slide --all
    print(f'\n🖼 [5/5] 渲染 HTML + 构建 PDF')
    rc = run('render_slide.py', project_root, '--all')
    if rc != 0:
        print('  ✗ render_slide.py 失败', file=sys.stderr)
        return 1

    # 9. build_pdf
    pdf_out = args.output or str(project_root / 'build' / f'{safe_name}.pdf')
    rc = run('build_pdf.py', project_root, '--output', pdf_out)
    if rc != 0:
        print('  ✗ build_pdf.py 失败', file=sys.stderr)
        return 1

    print(f'\n✅ 完成! PDF: {pdf_out}')
    print(f'   项目目录: {project_root}')
    return 0


# ================================================================
# subcommand: re-render (重渲染指定页)
# ================================================================
def cmd_rerender(args):
    """只重新渲染指定页面"""
    project_root = Path(args.project).resolve()
    if not (project_root / 'deck.yaml').exists():
        print(f'✗ deck.yaml 不存在: {project_root}')
        return 1
    slides = args.slides.split(',') if args.slides else []
    print(f'重渲染: {slides or "[全部]"}')
    if args.slides == 'all' or not slides:
        run('render_slide.py', project_root, '--all')
    else:
        for sid in slides:
            run('render_slide.py', project_root, sid.strip())
    run('build_pdf.py', project_root)
    return 0


# ================================================================
# subcommand: rebuild (重新渲染全部 + 构建 PDF)
# ================================================================
def cmd_rebuild(args):
    project_root = Path(args.project).resolve()
    if not (project_root / 'deck.yaml').exists():
        print(f'✗ deck.yaml 不存在: {project_root}')
        return 1
    run('render_slide.py', project_root, '--all')
    if not getattr(args, 'skip_auto_fix', False):
        # 排版自动调节: 检测溢出,注入 --text-scale,回写 slides/*.html
        run('check_overflow.py', project_root)
    run('build_pdf.py', project_root)
    return 0


# ================================================================
# subcommand: fix-layout (只跑自动排版调节,不重渲)
# ================================================================
def cmd_fix_layout(args):
    """只跑排版自动调节 (检测溢出 + 自动降级 --text-scale + 重建 PDF)"""
    project_root = Path(args.project).resolve()
    if not (project_root / 'deck.yaml').exists():
        print(f'✗ deck.yaml 不存在: {project_root}')
        return 1
    extra = []
    if getattr(args, 'slides', None):
        extra += ['--slides', args.slides]
    if getattr(args, 'dry_run', False):
        extra += ['--dry-run']
    rc = run('check_overflow.py', project_root, *extra)
    if rc != 0:
        return rc
    if not getattr(args, 'dry_run', False):
        run('build_pdf.py', project_root)
    return 0


# ================================================================
# subcommand: parse-pdf / parse-excel / render / pdf (单步调试)
# ================================================================
def cmd_parse_pdf(args):
    run('parse_v2_pdf.py', Path(args.project).resolve())

def cmd_parse_excel(args):
    run('parse_excel.py', Path(args.project).resolve())

def cmd_render(args):
    project_root = Path(args.project).resolve()
    target = args.slides if args.slides else '--all'
    if target != '--all' and not target.startswith('--'):
        run('render_slide.py', project_root, target)
    else:
        run('render_slide.py', project_root, '--all')

def cmd_pdf(args):
    out = ['--output', args.out] if args.out else []
    run('build_pdf.py', Path(args.project).resolve(), *out)


# ================================================================
# subcommand: book (图片+文字 → PDF 成果版)
# ================================================================
def cmd_book(args):
    """轻量模式: 图片+文字直接封装成 PDF"""
    extra = []
    if args.images:
        extra += ['--images', args.images]
    if args.config:
        extra += ['--config', args.config]
    if args.project:
        extra += ['--project', args.project]
    if args.out:
        extra += ['--out', args.out]
    extra += ['--layout', args.layout or '16:9', '--theme', args.theme or 'warm']
    rc = run('build_book.py', Path.cwd(), *extra)
    return rc


# ================================================================
# subcommand: protocol (PPT Layout Protocol v1.0 → PDF)
# ================================================================
def cmd_protocol(args):
    """协议模式: COZE 输出 page_protocol.json → 渲染 PDF"""
    project_root = Path(args.project).resolve() if args.project else Path.cwd()
    project_root.mkdir(parents=True, exist_ok=True)
    extra = ['--input', args.input]
    if args.skip_bg_gen:
        extra.append('--skip-bg-gen')
    if args.output:
        extra += ['--output', args.output]
    return run('render_protocol.py', project_root, *extra)


# ================================================================
# 主入口
# ================================================================
def main():
    ap = argparse.ArgumentParser(
        prog='ppt-engine',
        description='PPT 概念方案生成引擎 · 统一 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # COZE agent 全流程
  python main.py build \\
      --name "安岳柠檬冷链共享仓" \\
      --ref-pdf ./ref/v2.pdf \\
      --excel ./ref/指标表.xlsx \\
      --renders ./ref/效果图 \\
      --skip-bg-gen

  # 已有项目快速迭代
  python main.py re-render --project ./workdir/柠檬冷链 --slides 20,25
  python main.py rebuild --project ./workdir/柠檬冷链
""",
    )
    sub = ap.add_subparsers(dest='cmd', required=True)

    # build
    ap_b = sub.add_parser('build', help='全流程: 素材 → PDF')
    ap_b.add_argument('--name', required=True, help='项目名称')
    ap_b.add_argument('--project', default='', help='输出项目目录 (默认 workdir/<name>)')
    ap_b.add_argument('--ref-pdf', default='', help='参考 PDF (v2.pdf 等)')
    ap_b.add_argument('--md', default='', help='COZE 输出的 MD 草稿')
    ap_b.add_argument('--excel', default='', help='Excel 指标表')
    ap_b.add_argument('--renders', default='', help='效果图目录')
    ap_b.add_argument('--project-type', default='industrial_park',
                      choices=['industrial_park', 'real_estate', 'other'])
    ap_b.add_argument('--skip-bg-gen', action='store_true', help='跳过底图生成 (COZE 沙箱无图像 API)')
    ap_b.add_argument('--output', default='', help='输出 PDF 路径')
    ap_b.set_defaults(func=cmd_build)

    # re-render
    ap_rr = sub.add_parser('re-render', help='重渲染指定页 + 自动排版 + 重建 PDF')
    ap_rr.add_argument('--project', required=True, help='项目目录')
    ap_rr.add_argument('--slides', default='', help='slide_id 列表,逗号分隔 (如 20,22,25)')
    ap_rr.add_argument('--skip-auto-fix', action='store_true', help='跳过 check_overflow 排版自动调节')
    ap_rr.set_defaults(func=cmd_rerender)

    # rebuild
    ap_rb = sub.add_parser('rebuild', help='重新渲染全部 + 自动排版 + 重建 PDF')
    ap_rb.add_argument('--project', required=True, help='项目目录')
    ap_rb.add_argument('--skip-auto-fix', action='store_true', help='跳过 check_overflow 排版自动调节')
    ap_rb.set_defaults(func=cmd_rebuild)

    # fix-layout (只跑排版自动调节)
    ap_fl = sub.add_parser('fix-layout', help='排版自动调节: 检测溢出 + 自动降级 --text-scale + 重建 PDF')
    ap_fl.add_argument('--project', required=True, help='项目目录')
    ap_fl.add_argument('--slides', default='', help='只检查指定页,逗号分隔')
    ap_fl.add_argument('--dry-run', action='store_true', help='只检测,不写回 HTML')
    ap_fl.set_defaults(func=cmd_fix_layout)

    # 单步
    ap_pp = sub.add_parser('parse-pdf', help='只跑 parse_v2_pdf')
    ap_pp.add_argument('--project', required=True)
    ap_pp.set_defaults(func=cmd_parse_pdf)

    ap_px = sub.add_parser('parse-excel', help='只跑 parse_excel')
    ap_px.add_argument('--project', required=True)
    ap_px.set_defaults(func=cmd_parse_excel)

    ap_rd = sub.add_parser('render', help='只跑 render_slide')
    ap_rd.add_argument('--project', required=True)
    ap_rd.add_argument('--slides', default='--all')
    ap_rd.set_defaults(func=cmd_render)

    ap_pdf = sub.add_parser('pdf', help='只跑 build_pdf')
    ap_pdf.add_argument('--project', required=True)
    ap_pdf.add_argument('--out', default='')
    ap_pdf.set_defaults(func=cmd_pdf)

    # book (图片+文字 → PDF 成果版)
    ap_bk = sub.add_parser('book', help='轻量: 图片+文字 → PDF')
    ap_bk.add_argument('--images', default='', help='图片目录 (目录模式)')
    ap_bk.add_argument('--config', default='', help='pages.yaml (YAML 模式)')
    ap_bk.add_argument('--project', default='', help='项目名 (页眉)')
    ap_bk.add_argument('--out', default='成果版.pdf', help='输出 PDF')
    ap_bk.add_argument('--layout', default='16:9', choices=['16:9', 'A4'])
    ap_bk.add_argument('--theme', default='warm', choices=['warm', 'dark', 'plain'])
    ap_bk.set_defaults(func=cmd_book)

    # protocol (PPT Layout Protocol v1.0 → PDF)
    ap_pt = sub.add_parser('protocol', help='协议: page_protocol.json → PDF')
    ap_pt.add_argument('--input', required=True, help='page_protocol.json 路径')
    ap_pt.add_argument('--project', default='', help='项目目录 (默认当前目录)')
    ap_pt.add_argument('--skip-bg-gen', action='store_true', help='跳过底图生成')
    ap_pt.add_argument('--output', default='', help='输出 PDF 路径')
    ap_pt.set_defaults(func=cmd_protocol)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == '__main__':
    main()
