"""校验包结构、JSON Schema、模板与内部文件引用。"""
from pathlib import Path
import json
import sys
from jsonschema import Draft202012Validator
from workbench import ROOT, validate

def main():
    counts={'json_files':0,'schemas':0,'templates_and_examples':0,'role_prompts':0,'skills':0}
    for p in ROOT.rglob('*.json'):
        if 'runs' in p.relative_to(ROOT).parts: continue
        json.loads(p.read_text(encoding='utf-8')); counts['json_files']+=1
    for p in (ROOT/'schemas').glob('*.schema.json'):
        Draft202012Validator.check_schema(json.loads(p.read_text(encoding='utf-8')))
        counts['schemas']+=1
    for name in ['task','capabilities','approval','feedback','envelope']:
        validate(json.loads((ROOT/'templates'/f'{name}.json').read_text(encoding='utf-8')),name)
        counts['templates_and_examples']+=1
    validate(json.loads((ROOT/'examples/deck.example.json').read_text(encoding='utf-8')),'deck')
    counts['templates_and_examples']+=1
    for role in json.loads((ROOT/'config/agents.json').read_text(encoding='utf-8'))['roles']:
        assert (ROOT/role['prompt']).is_file(), role['prompt']
        counts['role_prompts']+=1
    for p in (ROOT/'.trae/skills').glob('*/SKILL.md'):
        s=p.read_text(encoding='utf-8')
        assert s.startswith('---\nname: ') and '\ndescription: ' in s and s.count('---')>=2
        counts['skills']+=1
    assert counts['skills'] >= 3, f"Expected at least 3 skills, got {counts['skills']}"
    expected=['workflow','io_policy','memory_policy','layout_profiles','markdown_style','source_registry','agents']
    for name in expected: assert (ROOT/'config'/f'{name}.json').is_file()
    bundle=json.loads((ROOT/'config/prompt_bundle.json').read_text(encoding='utf-8'))
    validate(bundle,'prompt_bundle')
    from workbench import sha
    for entry in bundle['messages']:
        p=ROOT/entry['source_path']
        assert sha(p)==entry['source_sha256'], '提示词JSON需要重新编译'
        assert p.read_text(encoding='utf-8')==entry['content']
    for p in (ROOT/'templates').glob('*.md'):
        s=p.read_text(encoding='utf-8'); assert s.startswith('---\n')
        for section in ['结论摘要','依据与范围','正文','待核问题','变更与审批','下一步']: assert section in s
    from validate_layout_table import validate_layout_table
    layout_result=validate_layout_table(ROOT)
    counts['layout_specification_rows']=layout_result['specification_rows']
    counts['layout_configuration_bindings']=layout_result['configuration_bindings']
    for relative in ['docs/README.md',layout_result['workbook'],'config/layout_table_mapping.json']:
        assert (ROOT/relative).is_file(), relative
    start=(ROOT/'TRAE_START_HERE.md').read_text(encoding='utf-8')
    assert 'docs/README.md' in start and layout_result['workbook'] in start
    assert (ROOT/'WORKBENCH_RULES_V7.md').is_file()
    assert (ROOT/'docs/09-对象级排版门控.md').is_file()
    gates=json.loads((ROOT/'config/object_layout_gates.json').read_text(encoding='utf-8'))['gates']
    assert [x['id'] for x in gates]==[f'L{i:02d}' for i in range(1,10)]
    counts['object_layout_gates']=len(gates)
    print(json.dumps({'status':'pass','counts':counts,'scope':'结构及契约，不代表TRAE端实际集成或PPT视觉验收'},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': sys.exit(main())
