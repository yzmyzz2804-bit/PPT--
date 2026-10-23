"""负向安全回归；不生成业务内容、真实审批或演示文稿。"""
from pathlib import Path
import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import workbench as w
import test_workbench as legacy


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.case=legacy.WorkbenchTests('test_schema_validation')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.addCleanup(self.case.tearDown)
        self.run=self.case.run

    def test_real_pdf_explicit_mapping_without_extraction(self):
        p=self.run/'00_inputs/real.pdf'
        from pypdf import PdfWriter; _pw=PdfWriter(); _pw.add_blank_page(width=1190.55,height=841.89); _f=open(p,'wb'); _pw.write(_f); _f.close()
        result=w.add_input(self.run,'00_inputs/real.pdf','PDF1')
        self.assertEqual(result['kind'],'reference')
        self.assertTrue(w.check_task(self.run))
        with self.assertRaises(w.GateError): w.add_input(self.run,'00_inputs/real.pdf','PDF2','image')

    def test_extension_and_size_policy(self):
        self.case.raw('00_inputs/unknown.exe','not executable')
        with self.assertRaises(w.GateError): w.add_input(self.run,'00_inputs/unknown.exe','X','reference')

    def test_pdf_spoof_kind_rejected(self):
        self.case.raw('00_inputs/x.pdf','not parsed in engineering test')
        t=self.case.get('task.json'); t['input_files'][0].update(path='00_inputs/x.pdf',kind='image',sha256=self.case.hash('00_inputs/x.pdf'))
        self.case.put('task.json',t)
        with self.assertRaises(w.GateError): w.check_task(self.run)

    def test_block_resume_no_stage_skip(self):
        s=w.block(self.run,'测试阻塞')
        self.assertEqual(s['resume_state'],'RECEIVED')
        with self.assertRaises(w.GateError): w.transition(self.run,'IDENTIFIED')
        self.assertEqual(w.resume(self.run)['state'],'RECEIVED')

    def test_resume_rechecks_hashes(self):
        w.block(self.run,'输入异常'); self.case.raw('00_inputs/source.md','changed')
        with self.assertRaises(w.GateError): w.resume(self.run)
        self.assertEqual(self.case.get('state.json')['state'],'BLOCKED')

    def test_pipeline_missing_approval_stops_and_deduplicates(self):
        (self.run/'approvals/contract.json').unlink()
        result=w.pipeline(self.run)
        self.assertEqual(result['advanced'],['IDENTIFIED','TAGGED','CONSTRAINTS_DRAFTED'])
        self.assertIn('缺少有效人工审批',result['error'])
        self.assertEqual(result['state']['resume_state'],'CONSTRAINTS_DRAFTED')
        seq=result['state']['sequence']; w.pipeline(self.run)
        self.assertEqual(self.case.get('state.json')['sequence'],seq)
        self.assertFalse((self.run/'approvals/contract.json').exists())
        w.resume(self.run)
        self.assertEqual(w.pipeline(self.run)['status'],'blocked')

    def test_rollback_archives_and_invalidates_approvals(self):
        self.case.advance_to('VERIFIED')
        before=self.case.hash('00_inputs/source.md')
        state=w.rollback(self.run,'evidence_error','回归测试')
        self.assertEqual(state['state'],'CONSTRAINTS_DRAFTED')
        self.assertFalse(list((self.run/'approvals').glob('*.json')))
        self.assertTrue(list((self.run/'audit').glob('rollback-*/approvals/contract.json')))
        self.assertEqual(before,self.case.hash('00_inputs/source.md'))
        with self.assertRaises(w.GateError): w.transition(self.run,'CONTRACT_APPROVED')
        with self.assertRaises(w.GateError): w.rollback(self.run,'release_error','不能前进')

    def test_control_lock_exclusion(self):
        (self.run/'.transition.lock').write_text('test')
        with self.assertRaises(w.GateError): w.block(self.run,'并发')

    def test_resume_rechecks_revoked_approval(self):
        self.case.advance_to('CONTRACT_APPROVED'); w.block(self.run,'等待复核')
        d=self.case.get('approvals/contract.json'); d['revoked']=True
        self.case.put('approvals/contract.json',d)
        with self.assertRaises(w.GateError): w.resume(self.run)
        self.assertEqual(self.case.get('state.json')['state'],'BLOCKED')

    def claims(self,dependencies,status='verified'):
        d=self.case.get('02_evidence/claims.json'); base=d['claims'][0]
        d['claims']=[]
        for cid,deps in dependencies.items():
            c=copy.deepcopy(base); c.update(claim_id=cid,kind='derived' if deps else 'fact',inputs=deps,formula='test' if deps else None,status=status)
            d['claims'].append(c)
        self.case.put('02_evidence/claims.json',d)

    def test_self_cycle(self):
        self.claims({'C1':['C1']})
        with self.assertRaisesRegex(w.GateError,'循环'): w.check_claims(self.run)

    def test_mutual_cycle(self):
        self.claims({'C1':['C2'],'C2':['C1']})
        with self.assertRaisesRegex(w.GateError,'循环'): w.check_claims(self.run)

    def test_missing_dependency(self):
        self.claims({'C1':['MISSING']})
        with self.assertRaises(w.GateError): w.check_claims(self.run)

    def test_unverified_input_to_verified_derived(self):
        self.claims({'C1':[],'C2':['C1']})
        d=self.case.get('02_evidence/claims.json'); d['claims'][0].update(status='unverified',critical=False)
        self.case.put('02_evidence/claims.json',d)
        with self.assertRaisesRegex(w.GateError,'依赖未核'): w.check_claims(self.run)

    def test_derived_without_inputs(self):
        self.claims({'C1':[]})
        d=self.case.get('02_evidence/claims.json'); d['claims'][0].update(kind='derived',formula='1')
        self.case.put('02_evidence/claims.json',d)
        with self.assertRaises(w.GateError): w.check_claims(self.run)

    def test_verified_dag(self):
        self.claims({'C1':[],'C2':['C1'],'C3':['C2','C1']})
        self.assertTrue(w.check_claims(self.run))

    def test_fake_render_and_qa_rejected(self):
        # 停掉旧状态机测试的格式模拟，必须执行真实检查。
        self.case.render_mock.stop()
        with self.assertRaises(w.GateError): w.check_artifacts(self.run,w.check_task(self.run))
        with self.assertRaises(w.GateError): w.check_qa(self.run)

    def test_renamed_text_pdf_and_pptx_rejected(self):
        self.case.render_mock.stop()
        for profile,ext in [('reporting','.pptx'),('print_a3','.pdf')]:
            path=self.run/('04_render/fake'+ext); path.write_text('not a render')
            with self.assertRaises(w.GateError): w.inspect_render(path,profile)

    def test_zip_named_pptx_rejected(self):
        from zipfile import ZipFile
        self.case.render_mock.stop()
        p=self.run/'04_render/fake.pptx'
        with ZipFile(p,'w') as z: z.writestr('hello.txt','not a presentation')
        with self.assertRaises(w.GateError): w.inspect_render(p,'reporting')

    def test_qa_rehashes_actual_files(self):
        self.case.raw('04_render/reporting.test.txt','changed after render')
        with self.assertRaisesRegex(w.GateError,'哈希变化'): w.check_qa(self.run)

    def test_real_blank_pdf_structure_not_visual_qa(self):
        from pypdf import PdfWriter
        self.case.render_mock.stop()
        p=self.run/'04_render/test.pdf'; writer=PdfWriter()
        writer.add_blank_page(width=420*72/25.4,height=297*72/25.4)
        with p.open('wb') as stream: writer.write(stream)
        w.inspect_render(p,'print_a3')
        # 没有因此将任何QA状态写为通过。
        self.assertEqual(self.case.get('state.json')['state'],'RECEIVED')

    def test_lock_manifest_missing_entry(self):
        d=self.case.get('config_lock.json'); d['files'].pop(next(iter(d['files'])))
        self.case.put('config_lock.json',d)
        with self.assertRaisesRegex(w.GateError,'清单不完整'): w.check_lock(self.run)

    def test_lock_version_independent_of_constraints(self):
        d=self.case.get('config_lock.json'); d['package_version']='6.2.0'; self.case.put('config_lock.json',d)
        with self.assertRaisesRegex(w.GateError,'版本不匹配'): w.check_lock(self.run)

    def test_lock_hash_drift(self):
        d=self.case.get('config_lock.json'); key=next(iter(d['files']))
        d['files'][key]='0'*64; self.case.put('config_lock.json',d)
        with self.assertRaisesRegex(w.GateError,'配置已改变'): w.check_lock(self.run)

    def test_migration_fresh_baseline_no_approval(self):
        # 只在v6.3内导入旧运行的独立测试副本。
        with tempfile.TemporaryDirectory(dir=w.ROOT/'runs') as temp:
            source=Path(temp)/'OLD'; shutil.copytree(self.run,source)
            original=w.sha(source/'config_lock.json')
            # init默认输出必须仍在当前工程；用随机ID避免覆盖。
            new_id='MIGRATE-'+Path(temp).name
            try:
                result=w.migrate(source,new_id); dest=Path(result['created'])
                self.assertEqual(w.load(dest/'state.json')['state'],'RECEIVED')
                self.assertEqual(w.load(dest/'task.json')['status'],'draft')
                self.assertFalse(list((dest/'approvals').glob('*.json')))
                self.assertTrue(all(x['status']=='unknown' for x in w.load(dest/'capabilities.json')['tools']))
                self.assertEqual(original,w.sha(source/'config_lock.json'))
                w.check_lock(dest)
            finally:
                shutil.rmtree(w.ROOT/'runs'/new_id,ignore_errors=True)


if __name__=='__main__': unittest.main()
