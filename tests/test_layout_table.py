from pathlib import Path
import sys,shutil,json,tempfile,unittest
from openpyxl import load_workbook
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_layout_table import ROOT,validate_layout_table

class LayoutTableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.r=Path(self.tmp.name)
        (self.r/'config').mkdir(); (self.r/'docs').mkdir()
        for p in ['config/layout_profiles.json','config/layout_table_mapping.json','docs/双版式版式规范对照表_A3与汇报版.xlsx']:
            shutil.copy2(ROOT/p,self.r/p)
    def tearDown(self): self.tmp.cleanup()
    def change_json(self,path,fn):
        p=self.r/path; d=json.loads(p.read_text(encoding='utf-8')); fn(d); p.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
    def change_cell(self,cell,value):
        p=self.r/'docs/双版式版式规范对照表_A3与汇报版.xlsx'
        w=load_workbook(p); w.active[cell]=value; w.save(p); w.close()
    def test_baseline(self): self.assertEqual(validate_layout_table(self.r)['specification_rows'],32)
    def test_title_value_drift(self):
        self.change_cell('C7','30')
        with self.assertRaises(ValueError): validate_layout_table(self.r)
    def test_config_value_drift(self):
        self.change_json('config/layout_profiles.json',lambda d:d['profiles']['print_a3']['font_pt'].update(body=16))
        with self.assertRaises(ValueError): validate_layout_table(self.r)
    def test_suggestion_not_silently_enabled(self):
        self.change_json('config/layout_profiles.json',lambda d:d['profiles']['reporting'].update(grid={'columns':12}))
        with self.assertRaises(ValueError): validate_layout_table(self.r)
    def test_missing_mapping_row(self):
        self.change_json('config/layout_table_mapping.json',lambda d:d['fields'].pop())
        with self.assertRaises(ValueError): validate_layout_table(self.r)
    def test_header_drift(self):
        self.change_cell('C4','旧版打印')
        with self.assertRaises(ValueError): validate_layout_table(self.r)

if __name__=='__main__': unittest.main()
