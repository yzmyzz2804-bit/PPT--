"""
check_overflow.py — 自动排版调节（Playwright 溢出检测 + --text-scale 降级）

在 render_slide.py 产出 slides/*.html 之后、build_pdf.py 之前运行。
逐页在 headless Chrome 里加载 slide HTML,对比 scrollHeight vs clientHeight
检测哪些文本容器被截断/溢出,自动把该页 .slide 的 --text-scale 从 1 降到 0.9/0.8/0.75,
然后用降级值重写 slides/*.html 并输出报告。

返回退出码: 0=全部 OK 或已自动修复; 1=检测到无法自动修复的溢出; 2=运行时错误。

用法:
    python check_overflow.py                               # 检查 PROJECT_ROOT 全部 slides
    python check_overflow.py --slides slide_03,slide_07    # 只检查指定页
    python check_overflow.py --dry-run                     # 只检测不写回
"""
import sys
import json
import argparse
from pathlib import Path

from _env import PROJECT_ROOT, DECK_PATH, SLIDES_DIR

# —— 需要检查溢出的选择器与触发阈值 ——
# (selector, 描述, 溢出容忍像素)
# tolerance: <= 2px 算正常 (子像素渲染误差/阴影),> 才算真溢出
_CHECK_SELECTORS = [
    (".page-title",     "页面标题",   4),
    (".card-text",      "卡片正文",   2),
    (".card-title",     "卡片标题",   3),
    (".page-subtitle",  "副标题",     2),
    (".cover-main",     "封面主标题", 4),
    (".cover-sub",      "封面副标题", 2),
    (".ch-name",        "章节名",     4),
    (".ch-desc",        "章节描述",   4),
    (".data-label",     "数据标签",   2),
    (".compare-title",  "对比标题",   3),
    (".compare-item",   "对比项",     3),
    (".feature-list li","列表项",     2),
    # 容器级: .slide-content 整体不能溢出 .slide
    (".slide-content",  "内容区",     8),
]

# --text-scale 降级阶梯 (依次尝试直到无溢出或到下限)
_SCALE_STEPS = [0.92, 0.84, 0.76, 0.70]
_MIN_SCALE = 0.70


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        print('✗ 需要 playwright: pip install playwright', file=sys.stderr)
        sys.exit(2)


# —— 在浏览器里跑的 JS: 返回本页所有溢出容器的详情 ——
_CHECK_JS = f"""
() => {{
    const results = [];
    const selectors = {json.dumps(_CHECK_SELECTORS)};
    for (const [sel, label, tol] of selectors) {{
        const elems = document.querySelectorAll(sel);
        elems.forEach((el, i) => {{
            const ch = el.clientHeight;
            const sh = el.scrollHeight;
            const cw = el.clientWidth;
            const sw = el.scrollWidth;
            const h_overflow = sh - ch - tol > 0;
            const w_overflow = sw - cw - tol > 0;
            if (h_overflow || w_overflow) {{
                results.push({{
                    selector: sel,
                    label: label,
                    index: i,
                    clientH: ch,
                    scrollH: sh,
                    clientW: cw,
                    scrollW: sw,
                    overflowH: Math.max(0, sh - ch),
                    overflowW: Math.max(0, sw - cw),
                }});
            }}
        }});
    }}
    return results;
}}
"""


def _inject_text_scale(html: str, scale: float) -> str:
    """找到 .slide 元素,注入 --text-scale: X; 到其 style (或新建 style 属性)。
    替换已有的 --text-scale 值(可能是之前注入的),或追加。"""
    import re
    # 匹配 <div class="slide ..." style="...">
    pattern = re.compile(r'(<div\s+class="slide[^"]*"\s*)(style=")([^"]*)(")')
    m = pattern.search(html)
    if not m:
        # .slide 没有 style 属性 → 加上
        pattern2 = re.compile(r'(<div\s+class="slide[^"]*")')
        m2 = pattern2.search(html)
        if not m2:
            return html  # 没有 .slide?
        return html[:m2.end()] + f' style="--text-scale: {scale};"' + html[m2.end():]

    head, style_attr, style_val, tail = m.group(1), m.group(2), m.group(3), m.group(4)
    # 替换已有的 --text-scale
    new_val = re.sub(r'--text-scale\s*:\s*[^;]+;?', '', style_val).strip()
    if new_val:
        new_val = new_val.rstrip('; ') + f'; --text-scale: {scale};'
    else:
        new_val = f'--text-scale: {scale};'
    return html[:m.start()] + head + style_attr + new_val + tail + html[m.end():]


def check_one_slide(slide_html_path: Path, browser) -> dict:
    """加载一页 HTML,返回 {slide_id, scale, overflows_before, overflows_after, fixed}"""
    slide_id = slide_html_path.stem

    abs_uri = slide_html_path.as_uri()
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto(abs_uri)
    page.wait_for_load_state('networkidle')

    overflows_before = page.evaluate(_CHECK_JS)
    current_scale = 1.0
    fixed = False
    overflows_after = overflows_before

    if overflows_before:
        # 依次降级 --text-scale
        for step in _SCALE_STEPS:
            # 必须把 scale 写回 HTML 再重新加载 (playwright 动态注入 CSS 变量对
            # -webkit-line-clamp 不生效,因为 line-clamp 在渲染期依赖初始字号计算行数)
            current_scale = step
            new_html = _inject_text_scale(slide_html_path.read_text(encoding='utf-8'), current_scale)
            slide_html_path.write_text(new_html, encoding='utf-8')
            page.reload()
            page.wait_for_load_state('networkidle')
            overflows_after = page.evaluate(_CHECK_JS)
            if not overflows_after:
                fixed = True
                break
        if overflows_after and current_scale <= _MIN_SCALE + 1e-9:
            # 到下限了仍有溢出,放弃修复,还原到 scale (保留最后尝试值,便于人工调)
            fixed = False

    page.close()
    return {
        'slide_id': slide_id,
        'scale_applied': current_scale,
        'overflow_count_before': len(overflows_before),
        'overflow_count_after': len(overflows_after),
        'fixed': fixed or (not overflows_before),
        'details_before': overflows_before[:10],  # 最多 10 条,防膨胀
        'details_after': overflows_after[:10],
    }


def main():
    ap = argparse.ArgumentParser(description='自动排版调节 -- Playwright 溢出检测')
    ap.add_argument('--slides', default='', help='逗号分隔的 slide_id 列表 (默认全部)')
    ap.add_argument('--dry-run', action='store_true', help='只检测,不写回 HTML')
    ap.add_argument('--output-report', default='', help='报告 JSON 输出路径 (默认 BUILD_DIR/overflow_report.json)')
    args = ap.parse_args()

    if not SLIDES_DIR.exists():
        print(f'✗ slides/ 目录不存在: {SLIDES_DIR}')
        sys.exit(2)

    targets = []
    if args.slides:
        for sid in args.slides.split(','):
            sid = sid.strip()
            p = SLIDES_DIR / f'{sid}.html'
            if p.exists():
                targets.append(p)
            else:
                print(f'  ⚠ 指定页不存在,跳过: {sid}')
    else:
        # 按 deck.yaml 中 slides 顺序检查 (保持页序一致)
        if DECK_PATH.exists():
            import yaml as _yaml
            deck = _yaml.safe_load(DECK_PATH.read_text(encoding='utf-8'))
            for s in deck.get('slides', []):
                p = SLIDES_DIR / f"{s['id']}.html"
                if p.exists():
                    targets.append(p)
        else:
            targets = sorted(SLIDES_DIR.glob('slide_*.html'))

    if not targets:
        print('✗ 没有可检查的 slides/*.html')
        sys.exit(0)

    print(f'\n🔍 [排版自动调节] 检查 {len(targets)} 页 HTML 溢出')
    print(f'   选择器: {len(_CHECK_SELECTORS)} 类关键容器')
    print(f'   scale 阶梯: 1.0 → {" → ".join(str(s) for s in _SCALE_STEPS)}')

    sync_playwright = _load_playwright()
    results = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, channel='chrome')
        except Exception:
            browser = pw.chromium.launch(headless=True)

        for i, html_path in enumerate(targets, 1):
            slide_id = html_path.stem
            print(f'  [{i}/{len(targets)}] {slide_id} ...', end=' ', flush=True)

            if args.dry_run:
                # dry-run 模式: 不改 HTML
                page = browser.new_page(viewport={'width': 1920, 'height': 1080})
                page.goto(html_path.as_uri())
                page.wait_for_load_state('networkidle')
                ovf = page.evaluate(_CHECK_JS)
                page.close()
                results.append({
                    'slide_id': slide_id,
                    'scale_applied': 1.0,
                    'overflow_count_before': len(ovf),
                    'overflow_count_after': len(ovf),
                    'fixed': len(ovf) == 0,
                    'details_before': ovf[:10],
                    'details_after': ovf[:10],
                })
                status = '✓' if not ovf else f'⚠ {len(ovf)}'
                print(status)
            else:
                r = check_one_slide(html_path, browser)
                results.append(r)
                if r['fixed']:
                    if r['scale_applied'] < 1.0:
                        print(f'✓ 自动修复 (--text-scale={r["scale_applied"]})')
                    else:
                        print('✓')
                else:
                    print(f'✗ 无法自动修复 ({r["overflow_count_after"]} 处溢出,scale={r["scale_applied"]})')

        browser.close()

    # 输出报告
    report = {
        'project_root': str(PROJECT_ROOT),
        'total_pages': len(results),
        'fixed_pages': sum(1 for r in results if r['fixed']),
        'pages_remaining_overflow': sum(1 for r in results if not r['fixed']),
        'dry_run': args.dry_run,
        'steps': _SCALE_STEPS,
        'min_scale': _MIN_SCALE,
        'results': results,
    }

    if args.output_report:
        report_path = Path(args.output_report)
    else:
        from _env import BUILD_DIR
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        report_path = BUILD_DIR / 'overflow_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    fixed_cnt = report['fixed_pages']
    fail_cnt = report['pages_remaining_overflow']
    print(f'\n📊 [排版自动调节] {fixed_cnt}/{len(results)} 页 OK (其中 {sum(1 for r in results if r["scale_applied"] < 1.0)} 页被自动缩放)')
    if fail_cnt:
        print(f'   ✗ {fail_cnt} 页仍有溢出,见报告: {report_path}')
        return 1
    print(f'   ✓ 全部通过,报告: {report_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
