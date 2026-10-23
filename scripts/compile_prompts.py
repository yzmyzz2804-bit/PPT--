"""将人可维护的Markdown提示词编译成JSON载入清单；不调用模型。"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def compile_bundle():
    roles=json.loads((ROOT/'config/agents.json').read_text(encoding='utf-8'))['roles']
    entries=[]
    for r in roles:
        path=ROOT/r['prompt']
        entries.append({'id':r['id'],'role':'system' if r['id']=='controller' else 'task_instructions',
                        'source_path':r['prompt'],'source_sha256':digest(path),'content':path.read_text(encoding='utf-8')})
    bundle={'version':'7.2.0','format':'application_prompt_bundle_v1',
            'execution':'由宿主按当前阶段选取messages，不是TRAE官方导入API或自动执行文件。',
            'resident_rule_path':'integration/PROJECT_RULES.md',
            'per_call_contract':{'input':['run_id','role','phase','input_refs','approved_scope'],
                                 'output_schema':'schemas/envelope.schema.json',
                                 'output':'仅JSON，无代码围栏；业务产物另外落盘并在output_refs列路径与SHA。'},
            'variable_binding':{'run_id':'task.run_id','objective':'task.objective','audience':'task.audience',
                                'mode':'task.mode','profiles':'task.requested_profiles','run_root':'runs/{run_id}',
                                'unknown_policy':'必填业务值缺失阻塞；不把null直接插成正文。'},
            'messages':entries}
    dump(ROOT/'config/prompt_bundle.json',bundle)
    return bundle

if __name__=='__main__':
    b=compile_bundle(); print(json.dumps({'compiled_prompts':len(b['messages']),'output':'config/prompt_bundle.json'},ensure_ascii=False))
