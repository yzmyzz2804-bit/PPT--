from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workbench as w

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        # 旧状态机测试仅模拟渲染能力；真实格式拒绝在test_v63单独验证。
        self.render_mock=patch.object(w,'inspect_render',return_value=None)
        self.render_mock.start()
        self.addCleanup(self.render_mock.stop)
        self.tmp=tempfile.TemporaryDirectory()
        self.run=w.init('TEST-RUN',self.tmp.name)
        self.populate()

    def tearDown(self): self.tmp.cleanup()

    def put(self,path,d): w.write(self.run/path,d)
    def get(self,path): return w.load(self.run/path)
    def hash(self,path): return w.sha(self.run/path)
    def raw(self,path,s):
        p=self.run/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')

    def grant(self,gate,target,scope=None):
        ep=f'approvals/{gate}.evidence.md'
        self.raw(ep,'仅单元测试模拟人工凭据；不是真实用户批准。')
        self.put(f'approvals/{gate}.json',{'approval_id':'TEST-'+gate,'run_id':'TEST-RUN','gate':gate,'target_path':target,'target_sha256':self.hash(target),'scope':scope or 'gate:'+gate,'decision':'approved','actor':'TEST-HUMAN','recorded_by':'TEST-HOST','evidence_path':ep,'evidence_sha256':self.hash(ep),'confirmed_at':w.now(),'revoked':False})

    def populate(self):
        rid='TEST-RUN'
        self.raw('00_inputs/source.md','# 测试源\n已知测试值100，不代表真实业务。')
        task=self.get('task.json')
        task.update(title='门控演示',audience='测试者',objective='离线测试门控',status='ready',input_files=[{'asset_id':'A1','path':'00_inputs/source.md','sha256':self.hash('00_inputs/source.md'),'kind':'minutes'}])
        self.put('task.json',task)
        caps=self.get('capabilities.json')
        caps['checked_at']=w.now()
        for c in caps['tools']:
            c.update(status='available',tool_name='UNIT-TEST-MOCK',evidence='仅测试模拟，不代表真实工具')
        self.put('capabilities.json',caps)
        self.put('01_memory/intake.json',{'run_id':rid,'files':[{'asset_id':'A1','path':'00_inputs/source.md','source_sha256':self.hash('00_inputs/source.md'),'page_count':1,'extracted_pages':1,'needs_ocr':False,'spot_checks':['p1 测试值100'],'status':'readable','issues':[]}]})
        self.put('01_memory/index.json',{'run_id':rid,'entries':[{'asset_id':'A1','kind':'minutes','tags':['测试'],'summary':'测试原件','path':'00_inputs/source.md','sha256':self.hash('00_inputs/source.md'),'version':'1','status':'active','supersedes':None}]})
        self.put('01_memory/constraints.json',{'run_id':rid,'version':'1','config_lock_sha256':self.hash('config_lock.json'),'mode':'preserve_optimize','protected_assets':[{'id':'P1','asset_id':'A1','locator':'p1','kind':'analysis','baseline_sha256':self.hash('00_inputs/source.md'),'allowed_operations':[]}],'allowed_changes':['创建演示副本'],'forbidden_actions':['覆盖原件'],'required_profiles':['reporting','print_a3'],'pending_decisions':[],'status':'ready_for_approval'})
        self.put('02_evidence/sources.json',{'run_id':rid,'sources':[{'source_id':'S1','kind':'local','locator':'00_inputs/source.md','snapshot_path':None,'publisher':None,'retrieved_at':w.now(),'applicable_version':None,'version_status':'not_applicable','sha256':self.hash('00_inputs/source.md'),'authority_status':'verified'}]})
        self.put('02_evidence/claims.json',{'run_id':rid,'claims':[{'claim_id':'C1','text':'测试值100','kind':'fact','value':100,'unit':'个','period':None,'denominator':None,'formula':None,'inputs':[],'source_ids':['S1'],'source_locators':['p1'],'critical':True,'status':'verified','method':'单元测试固定值比对，不代表业务核验','uncertainty':None}]})
        self.put('03_content/options.json',{'run_id':rid,'options':[{'option_id':k,'summary':'演示方案'+k,'tradeoffs':['仅测试'],'protected_changes':[]} for k in ['A','B']]})
        self.put('03_content/selection.json',{'run_id':rid,'option_id':'A','options_sha256':self.hash('03_content/options.json'),'rationale':'演示选择'})
        deck={'run_id':rid,'version':'1','claims_sha256':self.hash('02_evidence/claims.json'),'constraints_sha256':self.hash('01_memory/constraints.json'),'selection_sha256':self.hash('03_content/selection.json'),'pages':[],'protected_change_refs':[]}
        for profile,pid in [('reporting','R1'),('print_a3','P1')]:
            deck['pages'].append({'page_id':pid,'profile':profile,'type':'conclusion_evidence','title':'演示','core_message':'演示100','claim_ids':['C1'],'asset_ids':['A1'],'source_page_ids':[],'layout_id':'conclusion_evidence','speaker_notes':None,'protected_change_ids':[]})
        self.put('03_content/deck.json',deck)
        self.raw('05_qa/object-test-evidence.md','仅单元测试对象布局数据，不是实际业务视觉认证')
        self.put('03_content/object_layout.json',{'run_id':rid,'deck_sha256':self.hash('03_content/deck.json'),'source_page_count':1,'output_page_count':2,'objects':[{'object_id':'TEST-OBJ','source_page':1,'source_sha256':self.hash('00_inputs/source.md'),'kind':'paragraph','source_bbox':[0,0,100,100],'output_pages':[1,2],'status':'reflowed','visual_status':'pass','evidence_refs':['05_qa/object-test-evidence.md'],'measured_min_font_pt':14,'source_text':'测试内容','output_text':'测试内容','whole_lines':True}]})
        # Text payloads deliberately test file/hash control only, not real PPT/PDF rendering.
        files=[]
        for profile in ['reporting','print_a3']:
            path=f'04_render/{profile}.test.txt'; self.raw(path,'TEST PAYLOAD ONLY '+profile)
            files.append({'profile':profile,'path':path,'sha256':self.hash(path)})
        self.put('04_render/artifacts.json',{'run_id':rid,'deck_sha256':self.hash('03_content/deck.json'),'files':files})
        self.raw('05_qa/evidence.md','仅测试证据文件，不是视觉验收。')
        self.put('05_qa/report.json',{'run_id':rid,'deck_sha256':self.hash('03_content/deck.json'),'artifacts_sha256':self.hash('04_render/artifacts.json'),'checks':[{'id':c,'status':'pass','evidence':'05_qa/evidence.md'} for c in ['structure','numbers','visual','cross_variant','approvals','delivery']],'open_p0':0,'open_p1':0,'issues':[]})
        manifest={'run_id':rid,'deck_sha256':self.hash('03_content/deck.json'),'qa_sha256':self.hash('05_qa/report.json'),'artifacts_sha256':self.hash('04_render/artifacts.json'),'files':files}
        self.put('05_qa/release_manifest.json',manifest)
        copied=[]
        for f in files:
            path='06_release/'+Path(f['path']).name
            self.raw(path,(self.run/f['path']).read_text(encoding='utf-8'))
            copied.append(dict(f,path=path))
        self.put('06_release/manifest.json',dict(manifest,files=copied))
        self.put('07_feedback/feedback.json',{'run_id':rid,'package_version':'7.2.0','result':'accepted','issue_ids':[],'observations':['模拟运行'],'proposed_changes':[],'auto_apply':False})
        for gate,target in [('contract','01_memory/constraints.json'),('option','03_content/selection.json'),('content','03_content/deck.json'),('release','05_qa/release_manifest.json')]: self.grant(gate,target)

    def advance_to(self,target):
        states=w.load(w.ROOT/'config/workflow.json')['states'][:15]
        while self.get('state.json')['state']!=target:
            cur=self.get('state.json')['state']; w.transition(self.run,states[states.index(cur)+1])

    def test_full_state_chain(self):
        self.advance_to('RETROSPECTED')
        self.assertEqual(self.get('state.json')['sequence'],14)
        self.assertEqual(len((self.run/'audit/events.jsonl').read_text().splitlines()),14)

    def test_schema_validation(self): self.assertGreater(w.validate_run(self.run)['validated_documents'],3)
    def test_cannot_skip_stage(self):
        with self.assertRaises(w.GateError): w.check_transition(self.run,'RENDERED')
    def test_duplicate_init(self):
        with self.assertRaises(w.GateError): w.init('TEST-RUN',self.tmp.name)
    def test_path_escape(self):
        for path in ['../x','/etc/passwd','a/../../b','C:\\data']:
            with self.assertRaises(w.GateError): w.safe(self.run,path,False)
    def test_symlink_escape(self):
        (self.run/'bad').symlink_to(Path(self.tmp.name))
        with self.assertRaises(w.GateError): w.safe(self.run,'bad/x',False)
    def test_input_changed(self):
        self.raw('00_inputs/source.md','changed')
        with self.assertRaises(w.GateError): w.check_transition(self.run,'IDENTIFIED')
    def test_partial_extract(self):
        d=self.get('01_memory/intake.json'); d['files'][0]['extracted_pages']=0; self.put('01_memory/intake.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'IDENTIFIED')
    def test_missing_approval(self):
        self.advance_to('CONSTRAINTS_DRAFTED'); (self.run/'approvals/contract.json').unlink()
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTRACT_APPROVED')
    def test_approval_target_changed(self):
        self.advance_to('CONSTRAINTS_DRAFTED'); d=self.get('01_memory/constraints.json'); d['version']='2'; self.put('01_memory/constraints.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTRACT_APPROVED')
    def test_approval_evidence_changed(self):
        self.advance_to('CONSTRAINTS_DRAFTED'); self.raw('approvals/contract.evidence.md','tampered')
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTRACT_APPROVED')
    def test_wrong_scope(self):
        self.advance_to('CONSTRAINTS_DRAFTED'); d=self.get('approvals/contract.json'); d['scope']='gate:release'; self.put('approvals/contract.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTRACT_APPROVED')
    def test_revoked(self):
        self.advance_to('CONSTRAINTS_DRAFTED'); d=self.get('approvals/contract.json'); d['revoked']=True; self.put('approvals/contract.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTRACT_APPROVED')
    def test_critical_unverified(self):
        self.advance_to('CONTRACT_APPROVED'); d=self.get('02_evidence/claims.json'); d['claims'][0]['status']='unverified'; self.put('02_evidence/claims.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'VERIFIED')
    def test_deck_binding_stale(self):
        self.advance_to('OPTION_APPROVED'); d=self.get('02_evidence/claims.json'); d['claims'][0]['value']=101; self.put('02_evidence/claims.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTENT_READY')
    def test_cross_variant_missing(self):
        self.advance_to('OPTION_APPROVED'); d=self.get('03_content/deck.json'); d['pages'][1]['claim_ids']=[]; self.put('03_content/deck.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTENT_READY')
    def test_unknown_claim(self):
        self.advance_to('OPTION_APPROVED'); d=self.get('03_content/deck.json'); d['pages'][0]['claim_ids']=['BAD']; self.put('03_content/deck.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTENT_READY')
    def test_render_file_changed(self):
        self.advance_to('CONTENT_APPROVED'); self.raw('04_render/reporting.test.txt','changed')
        with self.assertRaises(w.GateError): w.check_transition(self.run,'RENDERED')
    def test_qa_not_checked(self):
        self.advance_to('RENDERED'); d=self.get('05_qa/report.json'); d['checks'][2]['status']='not_checked'; self.put('05_qa/report.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'QA_PASSED')
    def test_release_manifest_changed(self):
        self.advance_to('QA_PASSED'); d=self.get('05_qa/release_manifest.json'); d['files'][0]['sha256']='0'*64; self.put('05_qa/release_manifest.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'RELEASE_APPROVED')
    def test_publish_copy_changed(self):
        self.advance_to('RELEASE_APPROVED'); self.raw('06_release/reporting.test.txt','changed')
        with self.assertRaises(w.GateError): w.check_transition(self.run,'RELEASED')
    def test_protected_change_needs_approval(self):
        self.advance_to('OPTION_APPROVED')
        target='03_content/changes/C1.json'
        p={'change_id':'CH1','protected_asset_id':'P1','scope':'analysis:P1','before_sha256':self.hash('00_inputs/source.md'),'after_sha256':'1'*64,'reason':'测试变更'}
        self.put(target,p)
        d=self.get('03_content/deck.json'); d['protected_change_refs']=[{'target_path':target,'scope':p['scope'],'before_sha256':p['before_sha256'],'after_sha256':p['after_sha256']}]; d['pages'][0]['protected_change_ids']=['CH1']; self.put('03_content/deck.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONTENT_READY')
        self.grant('protected_change',target,p['scope'])
        w.check_transition(self.run,'CONTENT_READY')

    def test_missing_capability(self):
        d=self.get('capabilities.json'); d['tools'][0]['status']='unknown'; self.put('capabilities.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'IDENTIFIED')

    def test_config_lock_changed(self):
        self.advance_to('TAGGED')
        d=self.get('config_lock.json'); d['package_version']='other'; self.put('config_lock.json',d)
        c=self.get('01_memory/constraints.json'); c['config_lock_sha256']=self.hash('config_lock.json'); self.put('01_memory/constraints.json',c)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'CONSTRAINTS_DRAFTED')

    def test_web_snapshot_required(self):
        self.advance_to('CONTRACT_APPROVED')
        d=self.get('02_evidence/sources.json'); d['sources'][0].update(kind='web',locator='https://example.invalid/demo',snapshot_path=None)
        self.put('02_evidence/sources.json',d)
        with self.assertRaises(w.GateError): w.check_transition(self.run,'VERIFIED')

if __name__=='__main__': unittest.main()
