"""本地文件契约与状态门控。不是渲染器、审批身份服务或后台调度器。"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import sys
from contextlib import contextmanager
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VERSION = '7.2.0'

class GateError(Exception):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def write(p, data):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    temp=p.with_name(p.name+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(p)

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def safe(run, relative, must=True):
    if not isinstance(relative,str) or not relative or '\\' in relative:
        raise GateError('非法相对路径')
    p=Path(relative)
    if p.is_absolute() or '..' in p.parts or ':' in relative:
        raise GateError('拒绝路径逃逸: '+relative)
    target=(Path(run)/p).resolve()
    if not target.is_relative_to(Path(run).resolve()):
        raise GateError('拒绝符号链接逃逸: '+relative)
    if must and (not target.is_file() or target.stat().st_size==0):
        raise GateError('文件缺失或为空: '+relative)
    return target

def validate(data, schema_name):
    schema=load(ROOT/'schemas'/f'{schema_name}.schema.json')
    errors=sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e:str(e.path))
    if errors:
        e=errors[0]
        raise GateError(f'{schema_name}契约错误 {list(e.path)}: {e.message}')
    return data

def doc(run, relative, schema_name):
    data=validate(load(safe(run,relative)),schema_name)
    if data.get('run_id') != load(Path(run)/'state.json')['run_id']:
        raise GateError('运行ID不匹配: '+relative)
    return data

def check_sha(run, relative, expected):
    if sha(safe(run,relative)) != expected:
        raise GateError('文件哈希变化: '+relative)

def check_task(run):
    task=doc(run,'task.json','task')
    if task['status']!='ready' or not task['objective'] or not task['audience'] or not task['input_files']:
        raise GateError('任务未就绪: 请填写目标/受众/输入并标记ready')
    ids=[]
    policy=load(ROOT/'config/io_policy.json')['input']
    for item in task['input_files']:
        if not item['path'].startswith('00_inputs/'):
            raise GateError('输入必须位于00_inputs/')
        p=safe(run,item['path'])
        ext=p.suffix.lower()
        if ext not in policy['allowed_extensions'] or p.stat().st_size>policy['max_file_mb']*1024*1024:
            raise GateError('输入扩展名或大小不符合策略')
        mapped=policy.get('kind_by_extension',{}).get(ext)
        if mapped and item['kind']!=mapped:
            raise GateError('输入类型与扩展名不匹配，预期kind='+mapped)
        check_sha(run,item['path'],item['sha256']); ids.append(item['asset_id'])
    if len(ids)!=len(set(ids)):
        raise GateError('输入asset_id重复')
    return task

def check_lock(run):
    lock=doc(run,'config_lock.json','config_lock')
    state=doc(run,'state.json','state')
    if lock['package_version']!=VERSION or state['package_version']!=VERSION:
        raise GateError('冻结版本不匹配；使用migrate建立新运行，禁止原地重锁')
    if set(lock['files'])!=set(frozen_files()):
        raise GateError('冻结清单不完整或包含未知路径')
    for path,expected in lock['files'].items():
        p=safe(ROOT,path)
        if sha(p)!=expected:
            raise GateError('运行规则配置已改变，须新版本或重新建立审批基线: '+path)
    from validate_layout_table import validate_layout_table
    try: validate_layout_table(ROOT)
    except (ValueError,KeyError,OSError) as e:
        raise GateError('版式对照表校验失败: '+str(e)) from e
    return lock

def check_capabilities(run, required):
    d=doc(run,'capabilities.json','capabilities')
    entries={x['capability']:x for x in d['tools']}
    for name in required:
        x=entries.get(name)
        if not x or x['status']!='available' or not x['tool_name'] or not x['evidence']:
            raise GateError('缺少已实测能力: '+name)
    return d

def approval(run, gate, target, scope=None):
    target_sha=sha(safe(run,target))
    expected_scope=scope or 'gate:'+gate
    rid=load(Path(run)/'state.json')['run_id']
    for p in (Path(run)/'approvals').glob('*.json'):
        a=validate(load(p),'approval')
        if (a['run_id']==rid and a['gate']==gate and a['target_path']==target
            and a['target_sha256']==target_sha and a['scope']==expected_scope
            and a['decision']=='approved' and not a['revoked']):
            if not a['actor'].strip() or '[待填' in a['actor'] or '[待填' in a['confirmed_at']:
                continue
            check_sha(run,a['evidence_path'],a['evidence_sha256'])
            return a
    raise GateError(f'缺少有效人工审批: {gate} {target} scope={expected_scope}')

def check_intake(run, task):
    d=doc(run,'01_memory/intake.json','intake')
    items={x['asset_id']:x for x in d['files']}
    for source in task['input_files']:
        x=items.get(source['asset_id'])
        if not x or x['source_sha256']!=source['sha256'] or x['path']!=source['path']:
            raise GateError('识别未覆盖当前输入')
        if x['status']!='readable' or not x['spot_checks']:
            raise GateError('提取未验证或内容不可读')
        if x['page_count'] is not None and x['page_count']!=x['extracted_pages']:
            raise GateError('提取页数不完整')
    return d

def check_index(run, task):
    d=doc(run,'01_memory/index.json','index')
    ids=[]
    for x in d['entries']:
        check_sha(run,x['path'],x['sha256']); ids.append(x['asset_id'])
    if len(ids)!=len(set(ids)) or not set(x['asset_id'] for x in task['input_files']).issubset(ids):
        raise GateError('索引缺少输入或asset_id重复')
    return d

def check_constraints(run, task):
    d=doc(run,'01_memory/constraints.json','constraints')
    check_sha(run,'config_lock.json',d['config_lock_sha256'])
    if d['pending_decisions'] or d['status']=='draft':
        raise GateError('约束仍有待决策项或未就绪')
    if d['mode']!=task['mode'] or set(d['required_profiles'])!=set(task['requested_profiles']):
        raise GateError('约束与任务模式/版本不一致')
    asset_ids={x['asset_id'] for x in task['input_files']}
    for x in d['protected_assets']:
        if x['asset_id'] not in asset_ids:
            raise GateError('保护对象引用未知输入')
    return d

def check_claims(run):
    d=doc(run,'02_evidence/claims.json','claims')
    sources=doc(run,'02_evidence/sources.json','source')
    src={x['source_id']:x for x in sources['sources']}
    ids=[x['claim_id'] for x in d['claims']]
    if len(ids)!=len(set(ids)):
        raise GateError('claim_id重复')
    if len(src)!=len(sources['sources']):
        raise GateError('source_id重复')
    by_id={x['claim_id']:x for x in d['claims']}
    active=set(); complete=set()
    def visit(cid):
        if cid in active: raise GateError('claims循环依赖: '+cid)
        if cid in complete: return
        active.add(cid)
        x=by_id[cid]
        if x['kind']!='derived' and x['inputs']:
            raise GateError('非派生事实不能声明派生输入: '+cid)
        for dep in x['inputs']:
            if dep not in by_id: raise GateError('派生指标输入不存在')
            if x['status']=='verified' and (by_id[dep]['status']!='verified' or by_id[dep]['kind'] not in ['fact','derived']):
                raise GateError('已核派生指标依赖未核事实: '+cid)
            visit(dep)
        active.remove(cid); complete.add(cid)
    for cid in ids: visit(cid)
    for s in src.values():
        if s['kind']=='local': check_sha(run,s['locator'],s['sha256'])
        else:
            check_capabilities(run,['web_search','web_read'])
            if not s['snapshot_path']:
                raise GateError('网页来源缺少本地快照')
            check_sha(run,s['snapshot_path'],s['sha256'])
    for x in d['claims']:
        if x['critical'] and x['status']!='verified':
            raise GateError('关键事实待核或冲突: '+x['claim_id'])
        if x['kind'] in ['fact','derived'] and x['status']=='verified':
            if not x['source_ids'] or not x['source_locators']:
                raise GateError('已核事实缺来源定位')
        if any(s not in src for s in x['source_ids']):
            raise GateError('claim引用未知source_id')
        if x['kind']=='derived' and (not x['formula'] or not x['inputs']):
            raise GateError('派生指标缺公式/输入')
        if any(i not in ids for i in x['inputs']):
            raise GateError('派生指标输入不存在')
        if x['critical']:
            for sid in x['source_ids']:
                s=src[sid]
                if s['kind']=='web' and (s['authority_status']!='verified' or s['version_status']=='unknown'):
                    raise GateError('关键事实的网页来源主体/版本未确认')
    return d

def check_selection(run):
    opts=doc(run,'03_content/options.json','options')
    d=doc(run,'03_content/selection.json','selection')
    check_sha(run,'03_content/options.json',d['options_sha256'])
    if d['option_id'] not in [o['option_id'] for o in opts['options']]:
        raise GateError('选定方案不存在')
    return d

def check_deck(run, task):
    d=doc(run,'03_content/deck.json','deck')
    for key,path in [('claims_sha256','02_evidence/claims.json'),('constraints_sha256','01_memory/constraints.json'),('selection_sha256','03_content/selection.json')]:
        check_sha(run,path,d[key])
    claims=check_claims(run)
    valid_claims={x['claim_id'] for x in claims['claims']}
    critical={x['claim_id'] for x in claims['claims'] if x['critical']}
    asset_ids={x['asset_id'] for x in doc(run,'01_memory/index.json','index')['entries']}
    pids=[p['page_id'] for p in d['pages']]
    if len(pids)!=len(set(pids)):
        raise GateError('page_id重复')
    seen={p:set() for p in task['requested_profiles']}
    for p in d['pages']:
        if p['profile'] not in seen:
            raise GateError('未请求的版式')
        if not set(p['claim_ids']).issubset(valid_claims):
            raise GateError('页面引用未知claim_id')
        if not set(p['asset_ids']).issubset(asset_ids):
            raise GateError('页面引用未知asset_id')
        if not set(p['source_page_ids']).issubset(pids):
            raise GateError('页面映射引用未知page_id')
        seen[p['profile']].update(p['claim_ids'])
    for profile,ids in seen.items():
        if not any(p['profile']==profile for p in d['pages']) or not critical.issubset(ids):
            raise GateError('跨版缺失页面或关键claim: '+profile)
    change_ids=set()
    for c in d['protected_change_refs']:
        proposal=load(safe(run,c['target_path']))
        for field in ['change_id','protected_asset_id','scope','before_sha256','after_sha256','reason']:
            if not proposal.get(field): raise GateError('保护变更提案缺字段: '+field)
        if any(proposal[k]!=c[k] for k in ['scope','before_sha256','after_sha256']):
            raise GateError('保护变更与提案不匹配')
        protected=doc(run,'01_memory/constraints.json','constraints')['protected_assets']
        baseline=next((x for x in protected if x['id']==proposal['protected_asset_id']),None)
        if not baseline or baseline['baseline_sha256']!=c['before_sha256']:
            raise GateError('保护变更基线不匹配')
        approval(run,'protected_change',c['target_path'],c['scope'])
        change_ids.add(proposal['change_id'])
    if any(cid not in change_ids for p in d['pages'] for cid in p['protected_change_ids']):
        raise GateError('页面保护变更缺批准提案')
    return d

def check_artifacts(run, task):
    d=doc(run,'04_render/artifacts.json','artifacts')
    check_sha(run,'03_content/deck.json',d['deck_sha256'])
    check_object_gate(run)
    paths=[f['path'] for f in d['files']]
    if len(paths)!=len(set(paths)): raise GateError('渲染文件路径重复')
    for f in d['files']:
        check_sha(run,f['path'],f['sha256'])
        if not f['path'].startswith('04_render/'):
            raise GateError('渲染产物必须位于04_render/')
        inspect_render(safe(run,f['path']),f['profile'])
        if f['profile']=='print_a3' and Path(f['path']).suffix.lower()=='.pdf':
            from check_print_pdf import inspect_pdf
            layout=load(ROOT/'config/layout_profiles.json')['profiles']['print_a3']
            result=inspect_pdf(safe(run,f['path']),layout['canvas']['orientation'])
            if result['status']!='pass':
                raise GateError('A3打印PDF页框/方向不合格')
    if set(f['profile'] for f in d['files'])!=set(task['requested_profiles']):
        raise GateError('实际文件未覆盖请求的双版式')
    return d

def check_object_gate(run):
    from check_object_layout import check_manifest
    m=doc(run,'03_content/object_layout.json','object_layout')
    check_sha(run,'03_content/deck.json',m['deck_sha256'])
    task=check_task(run)
    known={x['sha256'] for x in task['input_files']}
    for item in m['objects']:
        if item['source_sha256'] not in known:
            raise GateError('对象来源SHA不匹配当前输入')
        for evidence in item['evidence_refs']:safe(run,evidence)
    result=check_manifest(m)
    if result['status']!='pass':raise GateError('对象级排版门控失败: '+'; '.join(result['errors'][:8]))
    return result

def check_qa(run):
    check_artifacts(run,check_task(run))
    d=doc(run,'05_qa/report.json','qa')
    check_sha(run,'03_content/deck.json',d['deck_sha256'])
    check_sha(run,'04_render/artifacts.json',d['artifacts_sha256'])
    expected={'structure','numbers','visual','cross_variant','approvals','delivery'}
    ids=[c['id'] for c in d['checks']]
    if set(ids)!=expected or len(ids)!=6 or any(c['status']!='pass' for c in d['checks']) or d['open_p0'] or d['open_p1']:
        raise GateError('QA有缺项/未检查/失败/P0/P1')
    for c in d['checks']: safe(run,c['evidence'])
    return d

def check_release(run, path):
    d=doc(run,path,'release')
    for key,ref in [('deck_sha256','03_content/deck.json'),('qa_sha256','05_qa/report.json'),('artifacts_sha256','04_render/artifacts.json')]:
        check_sha(run,ref,d[key])
    source=doc(run,'04_render/artifacts.json','artifacts')
    expected=sorted((f['profile'],f['sha256']) for f in source['files'])
    actual=sorted((f['profile'],f['sha256']) for f in d['files'])
    if expected!=actual:
        raise GateError('发布清单不匹配实际渲染产物')
    for f in d['files']: check_sha(run,f['path'],f['sha256'])
    if path.startswith('06_release/') and any(not f['path'].startswith('06_release/') for f in d['files']):
        raise GateError('正式发布文件必须是06_release内的副本')
    return d

def check_transition(run, target, source=None):
    run=Path(run)
    state=doc(run,'state.json','state')
    cfg=load(ROOT/'config/workflow.json')
    edge=next((e for e in cfg['transitions'] if e['from']==(source or state['state']) and e['to']==target),None)
    if not edge: raise GateError(f'非法状态转移 {state["state"]} -> {target}')
    task=check_task(run)
    check_lock(run)
    check_capabilities(run,['file_read','human_approval'])
    if any(f['kind']=='ppt' for f in task['input_files']): check_capabilities(run,['ppt_extract'])
    idx=cfg['states'].index(target)
    for path in edge['required_artifacts']: safe(run,path)
    # Revalidate the entire current dependency chain, not just the newest output.
    if idx>=1: check_intake(run,task)
    if idx>=2: check_index(run,task)
    if idx>=3: check_constraints(run,task)
    if idx>=4: approval(run,'contract','01_memory/constraints.json')
    if idx>=5: check_claims(run)
    if idx>=6: doc(run,'03_content/options.json','options')
    if idx>=7:
        check_selection(run); approval(run,'option','03_content/selection.json')
    if idx>=8: check_deck(run,task)
    if idx>=9: approval(run,'content','03_content/deck.json')
    if idx>=10:
        required=['fonts','visual_inspection']
        if 'reporting' in task['requested_profiles']: required.append('ppt_edit')
        if any(p.startswith('print') for p in task['requested_profiles']): required.append('pdf_render')
        check_capabilities(run,required)
        check_artifacts(run,task)
    if idx>=11:
        check_qa(run); check_release(run,'05_qa/release_manifest.json')
    if idx>=12: approval(run,'release','05_qa/release_manifest.json')
    if idx>=13: check_release(run,'06_release/manifest.json')
    if idx>=14: doc(run,'07_feedback/feedback.json','feedback')
    return edge

@contextmanager
def run_lock(run):
    run=Path(run)
    # Exclusive lock for cooperating script processes; not OS permission isolation.
    lock=run/'.transition.lock'
    try:
        with lock.open('x',encoding='utf-8') as f: f.write(now())
    except FileExistsError as e:
        raise GateError('运行转移锁已存在；确认无执行进程后由人工清理') from e
    try:
        yield
    finally:
        lock.unlink()

def record_state(run,target,resume=None,reason=None):
    run=Path(run); state=load(run/'state.json'); previous=state['state']
    state.update(state=target,resume_state=resume,sequence=state['sequence']+1,updated_at=now())
    write(run/'state.json',state)
    with (run/'audit/events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(run_id=state['run_id'],sequence=state['sequence'],
                               **{'from':previous,'to':target},time=state['updated_at'],reason=reason),ensure_ascii=False)+'\n')
    return state

def transition(run,target):
    with run_lock(run):
        check_transition(run,target)
        return record_state(run,target)

def frozen_files():
    files={}
    for folder in ['config','prompts','schemas','.trae/skills','integration','scripts']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
                files[p.relative_to(ROOT).as_posix()]=sha(p)
    for relative in ['WORKBENCH_RULES_V7.md','docs/09-对象级排版门控.md','docs/README.md','docs/双版式版式规范对照表_A3与汇报版.xlsx']:
        files[relative]=sha(ROOT/relative)
    return files

def inspect_render(path,profile):
    """格式与可解析性检查，不冒充视觉/内容核验。"""
    try:
        if profile=='reporting':
            if path.suffix.lower()!='.pptx': raise ValueError('汇报产物必须为.pptx')
            from zipfile import ZipFile
            from xml.etree import ElementTree as ET
            with ZipFile(path) as z:
                if z.testzip(): raise ValueError('PPTX压缩包损坏')
                ct=ET.fromstring(z.read('[Content_Types].xml'))
                expected='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
                if not any(x.get('PartName')=='/ppt/presentation.xml' and x.get('ContentType')==expected for x in ct):
                    raise ValueError('不是PPTX主文档')
            from pptx import Presentation
            if not len(Presentation(path).slides): raise ValueError('PPTX无页面')
        else:
            if path.suffix.lower()!='.pdf': raise ValueError('打印产物必须为.pdf')
            from pypdf import PdfReader
            with path.open('rb') as stream:
                if stream.read(5)!=b'%PDF-': raise ValueError('PDF签名错误')
            reader=PdfReader(path,strict=True)
            if reader.is_encrypted or not len(reader.pages): raise ValueError('PDF加密或无页面')
    except Exception as e:
        raise GateError('实际渲染格式无效: '+path.name+': '+str(e)) from e

def block(run,reason):
    if not reason.strip(): raise GateError('阻塞原因不能为空')
    with run_lock(run):
        s=doc(run,'state.json','state')
        if s['state']=='BLOCKED': return s
        return record_state(run,'BLOCKED',s['state'],reason)

def resume(run):
    with run_lock(run):
        s=doc(run,'state.json','state')
        states=load(ROOT/'config/workflow.json')['states'][:-1]
        target=s['resume_state']
        if s['state']!='BLOCKED' or target not in states: raise GateError('没有有效恢复点')
        check_task(run); check_lock(run)
        # 对恢复点重放入站校验，但不写伪造的中间状态。
        if target!='RECEIVED': check_transition(run,target,source=states[states.index(target)-1])
        return record_state(run,target,reason='已重新验证恢复点；未越过下一道审批')

def pipeline(run):
    """只推进已存在且通过校验的产物；不生产内容、能力或审批。"""
    cfg=load(ROOT/'config/workflow.json'); advanced=[]
    while True:
        s=doc(run,'state.json','state')
        if s['state']=='BLOCKED': return dict(status='blocked',advanced=advanced,state=s)
        edge=next((x for x in cfg['transitions'] if x['from']==s['state']),None)
        if not edge: return dict(status='complete',advanced=advanced,state=s)
        try: transition(run,edge['to']); advanced.append(edge['to'])
        except (GateError,ValueError,OSError,KeyError) as e:
            return dict(status='blocked',error=str(e),advanced=advanced,state=block(run,str(e)))

def rollback(run,kind,reason):
    """保守归档全部审批；不删除或改写业务文件。"""
    import shutil
    if not reason.strip(): raise GateError('回退原因不能为空')
    cfg=load(ROOT/'config/workflow.json'); states=cfg['states'][:-1]
    if kind not in cfg['rollback']: raise GateError('未知回退类型')
    target=cfg['rollback'][kind]
    with run_lock(run):
        s=doc(run,'state.json','state'); current=s['resume_state'] if s['state']=='BLOCKED' else s['state']
        if current not in states or states.index(target)>=states.index(current): raise GateError('回退必须指向更早状态')
        archive=Path(run)/'audit'/('rollback-'+str(s['sequence']+1))
        archive.mkdir()
        # 先进入BLOCKED；中途失败不会留下仍可发布的状态。
        record_state(run,'BLOCKED',target,'回退进行中: '+reason)
        for folder in ['01_memory','02_evidence','03_content','04_render','05_qa','06_release','07_feedback','approvals']:
            shutil.copytree(Path(run)/folder,archive/folder)
        for p in (Path(run)/'approvals').glob('*.json'): p.unlink()
        write(archive/'control.json',dict(reason=reason,target=target,approvals_invalidated='all'))
        return record_state(run,target,reason=reason+'；全部审批归档失效，产物保留待重验')

def add_input(run,path,asset_id,kind=None):
    """显式映射 PDF→reference；只登记已在00_inputs中的文件。"""
    with run_lock(run):
        if doc(run,'state.json','state')['state']!='RECEIVED': raise GateError('只能在RECEIVED登记输入')
        check_lock(run)
        p=safe(run,path)
        if not path.startswith('00_inputs/'): raise GateError('输入必须位于00_inputs/')
        policy=load(ROOT/'config/io_policy.json')['input']
        mapped=policy.get('kind_by_extension',{}).get(p.suffix.lower())
        chosen=kind or mapped
        if not chosen or (mapped and chosen!=mapped): raise GateError('类型不明确或与扩展名映射冲突')
        t=doc(run,'task.json','task')
        if any(x['asset_id']==asset_id or x['path']==path for x in t['input_files']): raise GateError('输入ID或路径重复')
        if p.suffix.lower() not in policy['allowed_extensions'] or p.stat().st_size>policy['max_file_mb']*1024*1024: raise GateError('输入不符合策略')
        t['input_files'].append(dict(asset_id=asset_id,path=path,sha256=sha(p),kind=chosen))
        validate(t,'task'); write(Path(run)/'task.json',t)
        return dict(asset_id=asset_id,kind=chosen,note='仅登记文件与哈希；未提取内容或批准任务')

def migrate(run,new_id):
    """新运行迁移，仅复制原始输入与任务；不继承能力、产物或审批。"""
    import shutil
    run=Path(run)
    if not run.resolve().is_relative_to((ROOT/'runs').resolve()): raise GateError('迁移源必须是当前工程runs内的导入副本')
    with run_lock(run):
        task=doc(run,'task.json','task')
        for x in task['input_files']:
            if not x['path'].startswith('00_inputs/'): raise GateError('迁移输入路径非法')
            check_sha(run,x['path'],x['sha256'])
        dest=init(new_id)
        for x in task['input_files']:
            p=safe(dest,x['path'],False); p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(safe(run,x['path']),p)
        task.update(run_id=new_id,status='draft'); write(dest/'task.json',task)
        write(dest/'audit/migration.json',dict(source_run_id=load(run/'state.json')['run_id'],
              source_state_sha256=sha(run/'state.json'),source_lock_sha256=sha(run/'config_lock.json'),
              inherited_approvals=False,inherited_capabilities=False))
        return dict(created=str(dest),status='draft',note='原运行未重锁；所有审批须重新建立')

def init(run_id, base=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',run_id):
        raise GateError('run_id仅允许字母数字下划线连字符')
    run=(Path(base) if base else ROOT/'runs')/run_id
    if run.exists(): raise GateError('运行目录已存在；拒绝覆盖')
    run.mkdir(parents=True)
    for name in ['00_inputs','01_memory','02_evidence','03_content','04_render','05_qa','06_release','07_feedback','approvals','audit']:
        (run/name).mkdir()
    for name in ['task','capabilities']:
        data=load(ROOT/'templates'/f'{name}.json'); data['run_id']=run_id
        write(run/f'{name}.json',data)
    write(run/'config_lock.json',{'run_id':run_id,'package_version':VERSION,'files':frozen_files()})
    write(run/'state.json',{'run_id':run_id,'state':'RECEIVED','resume_state':None,'sequence':0,'updated_at':now(),'package_version':VERSION})
    (run/'handoff.md').write_text((ROOT/'templates/handoff.md').read_text(encoding='utf-8'),encoding='utf-8')
    return run

def validate_run(run):
    run=Path(run)
    for name in ['task','capabilities','state','config_lock']: doc(run,name+'.json',name)
    mapping={'01_memory/intake.json':'intake','01_memory/index.json':'index','01_memory/constraints.json':'constraints','02_evidence/sources.json':'source','02_evidence/claims.json':'claims','03_content/options.json':'options','03_content/selection.json':'selection','03_content/deck.json':'deck','04_render/artifacts.json':'artifacts','05_qa/report.json':'qa','05_qa/release_manifest.json':'release','06_release/manifest.json':'release','07_feedback/feedback.json':'feedback'}
    count=4
    for path,name in mapping.items():
        if (run/path).exists(): doc(run,path,name); count+=1
    for p in (run/'approvals').glob('*.json'):
        doc(run,p.relative_to(run).as_posix(),'approval'); count+=1
    return {'validated_documents':count,'note':'结构通过不等于业务就绪；状态推进另执行check-transition'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('init'); p.add_argument('--run-id',required=True)
    for command in ['validate','status','check-transition','transition','block','resume','rollback','pipeline','add-input','migrate']:
        p=sub.add_parser(command); p.add_argument('--run',required=True)
        if command in ['check-transition','transition']: p.add_argument('--to',required=True)
        if command in ['block','rollback']: p.add_argument('--reason',required=True)
        if command=='rollback': p.add_argument('--kind',required=True)
        if command=='migrate': p.add_argument('--new-run-id',required=True)
        if command=='add-input':
            p.add_argument('--path',required=True); p.add_argument('--asset-id',required=True); p.add_argument('--kind')
    args=parser.parse_args()
    try:
        if args.command=='init': result={'created':str(init(args.run_id))}
        elif args.command=='validate': result=validate_run(Path(args.run))
        elif args.command=='status': result=doc(Path(args.run),'state.json','state')
        elif args.command=='check-transition': result={'eligible':True,'edge':check_transition(Path(args.run),args.to)}
        elif args.command=='block': result=block(args.run,args.reason)
        elif args.command=='resume': result=resume(args.run)
        elif args.command=='rollback': result=rollback(args.run,args.kind,args.reason)
        elif args.command=='pipeline':
            result=pipeline(args.run)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 2 if result['status']=='blocked' else 0
        elif args.command=='add-input': result=add_input(args.run,args.path,args.asset_id,args.kind)
        elif args.command=='migrate': result=migrate(args.run,args.new_run_id)
        else: result=transition(Path(args.run),args.to)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (GateError,ValueError,OSError,KeyError) as e:
        print(json.dumps({'status':'blocked','error':str(e)},ensure_ascii=False),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__': sys.exit(main())
