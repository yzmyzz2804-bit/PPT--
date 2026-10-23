"""只读核对副本保留、schema边界、版本和Python语法；不生成分发包。"""
from pathlib import Path
import ast
import hashlib
import json

root=Path(__file__).resolve().parents[1]
old=root.parent/'ai-ppt-workbench-v6.2-a3'
excluded={'FILE_MANIFEST.json','docs/验证结果.md','docs/validation-results.json'}
missing=[]; changed=[]; identical=0
for p in old.rglob('*'):
    if not p.is_file() or '__pycache__' in p.parts: continue
    rel=p.relative_to(old).as_posix()
    if rel in excluded: continue
    q=root/rel
    if not q.is_file(): missing.append(rel)
    elif hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(q.read_bytes()).digest(): changed.append(rel)
    else: identical+=1
assert not missing,missing
schema_changes=[p for p in changed if p.startswith('schemas/')]
assert schema_changes==['schemas/prompt_bundle.schema.json'],schema_changes
syntax=0
for folder in ['scripts','tests']:
    for p in (root/folder).glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'),filename=str(p)); syntax+=1
for p in (root/'config').glob('*.json'):
    d=json.loads(p.read_text(encoding='utf-8'))
    if 'version' in d: assert d['version']=='7.2.0',p
assert (old/'FILE_MANIFEST.json').is_file()
assert (old/'docs/validation-results.json').is_file()
assert not (root/'FILE_MANIFEST.json').exists()
assert not list(root.rglob('__pycache__'))
assert (old/'CHANGELOG.md').read_text(encoding='utf-8').split('\n',1)[1] in (root/'CHANGELOG.md').read_text(encoding='utf-8')
print(json.dumps(dict(status='pass',python_syntax_files=syntax,retained_identical_files=identical,
                     missing_original_files=missing,changed_files=changed,
                     schema_changes=schema_changes,original_manifest_and_results_retained=True,
                     active_version='7.2.0',original_read_only=True),ensure_ascii=False,indent=2))
