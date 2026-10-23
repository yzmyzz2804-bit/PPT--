#!/usr/bin/env python3
"""
coze_runner.py - COZE Agent 一键调用入口

用法 (COZE Code 节点直接粘贴):
    python coze_runner.py \
        --name "安岳县柠檬冷链共享仓建设项目" \
        --ref-pdf /tmp/coze_uploads/ref.pdf \
        --excel /tmp/coze_uploads/指标表.xlsx \
        --renders /tmp/coze_uploads/效果图 \
        --zip-path /tmp/coze_uploads/ppt-engine.zip

输出 JSON (COZE agent 据此判断):
    {"success": true,  "pdf_path": "/tmp/coze_output/xxx/build/xxx.pdf"}
    {"success": false, "error": "具体错误信息"}

设计要点:
  - 自包含: 首次运行解压 ZIP → pip install → playwright install chromium
  - 带缓存: engine 已解压 / 依赖已装就跳过
  - --skip-bg-gen 硬编码 (COZE 沙箱无图像 API)
  - 路径用 /tmp (COZE 沙箱标准临时目录)
"""
import sys
import os
import json
import shutil
import subprocess
import argparse
from pathlib import Path


# ========== 常量 ==========
ENGINE_DIR = Path('/tmp/ppt-engine')          # 解压后的引擎位置
ENGINE_MARK = ENGINE_DIR / 'main.py'           # 存在即解压完成的标记
CACHE_DIR = Path('/tmp/coze_cache')            # pip/playwright 缓存
PLAYWRIGHT_MARK = CACHE_DIR / '.playwright_ok'  # chromium 已安装标记


def _out(obj: dict):
    """输出 JSON 并退出"""
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0 if obj.get('success') else 1)


def _run(cmd: list, env: dict = None, capture: bool = True) -> tuple:
    """执行命令,返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(
            cmd,
            env=env or os.environ.copy(),
            capture_output=capture,
            text=True,
            timeout=600,
        )
        return r.returncode, r.stdout or '', r.stderr or ''
    except subprocess.TimeoutExpired as e:
        return -1, '', str(e)
    except Exception as e:
        return -1, '', str(e)


def ensure_engine(zip_path: str):
    """解压 ZIP + 安装依赖 (带缓存)"""
    zip_path = Path(zip_path)
    if not zip_path.exists():
        _out({'success': False, 'error': f'ppt-engine.zip 不存在: {zip_path}'})

    # 1. 解压
    if not ENGINE_MARK.exists():
        print('[coze] 解压 ppt-engine.zip ...', flush=True)
        shutil.rmtree(ENGINE_DIR, ignore_errors=True)
        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall('/tmp/')
        # ZIP 解压出来可能是 ppt-engine/ 子目录,也可能直接是文件
        if not ENGINE_MARK.exists():
            # 看看 /tmp/ 下有没有 ppt-engine 目录
            for item in Path('/tmp').iterdir():
                if item.is_dir() and (item / 'main.py').exists():
                    item.rename(ENGINE_DIR)
                    break
        if not ENGINE_MARK.exists():
            _out({'success': False, 'error': f'解压后找不到 main.py, 检查 ZIP 结构'})
    else:
        print('[coze] 引擎已解压,跳过', flush=True)

    # 2. pip install (带缓存)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pip_cache = CACHE_DIR / 'pip'
    pip_cache.mkdir(exist_ok=True)

    print('[coze] pip install -r requirements.txt ...', flush=True)
    rc, out, err = _run([
        sys.executable, '-m', 'pip', 'install',
        '-r', str(ENGINE_DIR / 'requirements.txt'),
        '--quiet',
        '--cache-dir', str(pip_cache),
    ])
    if rc != 0:
        _out({'success': False, 'error': f'pip install 失败: {err[-500:]}'})

    # 3. playwright install chromium (带缓存标记)
    if not PLAYWRIGHT_MARK.exists():
        print('[coze] playwright install chromium ...', flush=True)
        rc, out, err = _run([
            sys.executable, '-m', 'playwright', 'install', 'chromium',
        ])
        if rc != 0:
            print(f'  警告: playwright install 返回 {rc}, build_pdf 有 Chrome fallback', flush=True)
        PLAYWRIGHT_MARK.write_text('ok')
    else:
        print('[coze] playwright 已安装,跳过', flush=True)


def run_job(args):
    """按 mode 调 main.py build 或 book"""
    safe_name = args.name.replace('/', '_').replace('\\', '_')
    project_root = Path('/tmp/coze_output') / safe_name
    project_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env['PPT_ENGINE_ROOT'] = str(ENGINE_DIR)

    if args.mode == 'book':
        # 轻量模式: 图片(+文字)直接封装 PDF
        out_pdf = Path(args.out) if args.out else project_root / 'build' / f'{safe_name}.pdf'
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, str(ENGINE_DIR / 'main.py'), 'book',
            '--project', args.name,
            '--out', str(out_pdf),
            '--layout', args.layout or '16:9',
            '--theme', args.theme or 'warm',
        ]
        if args.config:
            cmd += ['--config', args.config]
        elif args.images:
            cmd += ['--images', args.images]
        else:
            _out({'success': False, 'error': 'book 模式必须提供 --images 或 --config'})
        print(f'[coze] $ {" ".join(cmd)}', flush=True)
        rc, out, err = _run(cmd, env=env, capture=False)
        if out_pdf.exists():
            _out({'success': True, 'pdf_path': str(out_pdf.resolve()),
                  'size_kb': out_pdf.stat().st_size // 1024, 'mode': 'book'})
        _out({'success': False, 'error': f'main.py book 返回 {rc}, 未找到 PDF', 'stderr': err[-300:]})

    if args.mode == 'protocol':
        # 协议模式: page_protocol.json → PDF
        if not args.input:
            _out({'success': False, 'error': 'protocol 模式必须提供 --input page_protocol.json'})
        out_pdf = Path(args.out) if args.out else project_root / 'build' / f'{safe_name}.pdf'
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, str(ENGINE_DIR / 'main.py'), 'protocol',
            '--input', args.input,
            '--project', str(project_root),
            '--skip-bg-gen',  # COZE 沙箱无图像 API
            '--output', str(out_pdf),
        ]
        print(f'[coze] $ {" ".join(cmd)}', flush=True)
        rc, out, err = _run(cmd, env=env, capture=False)
        if out_pdf.exists():
            _out({'success': True, 'pdf_path': str(out_pdf.resolve()),
                  'size_kb': out_pdf.stat().st_size // 1024, 'mode': 'protocol'})
        _out({'success': False, 'error': f'main.py protocol 返回 {rc}, 未找到 PDF',
              'stderr': err[-300:]})

    # 完整模式: 参考PDF+Excel+效果图 → 全流程
    renders_arg = ''
    if args.renders:
        renders_arg = str(Path(args.renders))
    cmd = [
        sys.executable,
        str(ENGINE_DIR / 'main.py'),
        'build',
        '--name', args.name,
        '--project', str(project_root),
        '--project-type', args.project_type or 'industrial_park',
        '--skip-bg-gen',  # COZE 沙箱必然没有图像 API
    ]
    if args.ref_pdf:
        cmd += ['--ref-pdf', args.ref_pdf]
    if args.excel:
        cmd += ['--excel', args.excel]
    if renders_arg:
        cmd += ['--renders', renders_arg]
    if args.md:
        cmd += ['--md', args.md]

    print(f'[coze] $ {" ".join(cmd)}', flush=True)
    rc, out, err = _run(cmd, env=env, capture=False)

    # 找输出 PDF
    pdf_candidates = list((project_root / 'build').glob('*.pdf')) if (project_root / 'build').exists() else []
    if pdf_candidates:
        pdf_path = str(pdf_candidates[0].resolve())
        size_kb = pdf_candidates[0].stat().st_size // 1024
        _out({'success': True, 'pdf_path': pdf_path, 'size_kb': size_kb, 'project': str(project_root)})
    else:
        # 没找到 PDF
        _out({
            'success': False,
            'error': f'main.py 返回 {rc}, 但 build/ 下无 PDF',
            'hint': '检查 deck.yaml 和 render_slide.py 输出',
        })


def main():
    ap = argparse.ArgumentParser(description='COZE Runner: 一键 PPT 生成')
    ap.add_argument('--mode', default='build', choices=['build', 'book', 'protocol'],
                    help='build=完整PPT流程 / book=图片+文字直接出PDF / protocol=协议JSON渲染')
    ap.add_argument('--name', required=True, help='项目名称')
    ap.add_argument('--ref-pdf', default='', help='参考 PDF (build 模式必须)')
    ap.add_argument('--excel', default='', help='Excel 指标表 (build 模式)')
    ap.add_argument('--renders', default='', help='效果图目录 (build 模式)')
    ap.add_argument('--md', default='', help='COZE MD 草稿 (build 模式)')
    ap.add_argument('--images', default='', help='图片目录 (book 模式)')
    ap.add_argument('--config', default='', help='pages.yaml (book 模式,含文字)')
    ap.add_argument('--input', default='', help='page_protocol.json (protocol 模式)')
    ap.add_argument('--out', default='', help='输出 PDF 路径 (book/protocol 模式)')
    ap.add_argument('--layout', default='16:9', choices=['16:9', 'A4'], help='book 模式版式')
    ap.add_argument('--theme', default='warm', choices=['warm', 'dark', 'plain'], help='book 模式主题')
    ap.add_argument('--project-type', default='industrial_park',
                    choices=['industrial_park', 'real_estate', 'other'])
    ap.add_argument('--zip-path', default='/tmp/coze_uploads/ppt-engine.zip',
                    help='ppt-engine.zip 的路径')
    args = ap.parse_args()

    # 校验必填
    if args.mode == 'build' and not args.ref_pdf:
        _out({'success': False, 'error': 'build 模式必须提供 --ref-pdf 参考 PDF'})
    if args.mode == 'protocol' and not args.input:
        _out({'success': False, 'error': 'protocol 模式必须提供 --input page_protocol.json'})

    try:
        ensure_engine(args.zip_path)
        run_job(args)
    except Exception as e:
        _out({'success': False, 'error': f'未预期异常: {type(e).__name__}: {str(e)}'})


if __name__ == '__main__':
    main()
