"""
_env.py - 环境变量 / 路径解析共享模块

包运行时,main.py 会设置:
    PPT_ENGINE_ROOT  → 引擎根目录 (templates/base.css/theme.json 所在地)
    PPT_PROJECT      → 项目根目录 (deck.yaml/slides/build/assets 所在地)

脚本独立运行时(开发调试):
    ENGINE_ROOT 默认 Path(__file__).parent.parent (包根)
    PROJECT_ROOT 默认 Path.cwd() 或 PPT_PROJECT 环境变量
"""
import os
from pathlib import Path

# 引擎根 (templates/base.css/theme.json)
ENGINE_ROOT = Path(os.environ.get('PPT_ENGINE_ROOT', str(Path(__file__).parent.parent))).resolve()

# 项目根 (deck.yaml/slides/build/assets)
PROJECT_ROOT = Path(os.environ.get('PPT_PROJECT', str(Path.cwd()))).resolve()

# 便捷导出
DECK_PATH = PROJECT_ROOT / 'deck.yaml'

# 主题: 项目目录下若有 theme.json 则优先(主题隔离),否则用引擎全局主题
_PROJECT_THEME = PROJECT_ROOT / 'theme.json'
THEME_PATH = _PROJECT_THEME if _PROJECT_THEME.exists() else ENGINE_ROOT / 'theme.json'
TEMPLATES_DIR = ENGINE_ROOT / 'templates'
SLIDES_DIR = PROJECT_ROOT / 'slides'
BUILD_DIR = PROJECT_ROOT / 'build'
ASSETS_DIR = PROJECT_ROOT / 'assets'
BG_DIR = ASSETS_DIR / 'images' / 'bg'


def ensure_project_dirs():
    """确保项目根目录下必要的子目录存在"""
    for d in [SLIDES_DIR, BUILD_DIR, ASSETS_DIR, BG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def print_paths():
    """调试用: 打印当前解析的路径"""
    print(f'  ENGINE_ROOT = {ENGINE_ROOT}')
    print(f'  PROJECT_ROOT= {PROJECT_ROOT}')
    print(f'  DECK_PATH   = {DECK_PATH}')
    print(f'  TEMPLATES   = {TEMPLATES_DIR}')
