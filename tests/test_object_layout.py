from pathlib import Path
import sys,copy,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_object_layout import check_manifest
class ObjectTests(unittest.TestCase):
    def base(self):return {'run_id':'TEST','deck_sha256':'0'*64,'source_page_count':1,'output_page_count':1,'objects':[{'object_id':'O1','source_page':1,'source_sha256':'0'*64,'kind':'paragraph','source_bbox':[0,0,100,100],'output_pages':[1],'status':'reflowed','visual_status':'pass','evidence_refs':['qa.md'],'measured_min_font_pt':14,'source_text':'原文100','output_text':'原文100','whole_lines':True}]}
    def test_paragraph(self):self.assertEqual(check_manifest(self.base())['status'],'pass')
    def test_text_changed(self):
        d=self.base();d['objects'][0]['output_text']='原文101';self.assertEqual(check_manifest(d)['status'],'fail')
    def test_small_font(self):
        d=self.base();d['objects'][0]['measured_min_font_pt']=11;self.assertEqual(check_manifest(d)['status'],'fail')
    def test_reference_not_reflow(self):
        d=self.base();d['objects'][0]['status']='reference';self.assertEqual(check_manifest(d)['status'],'fail')
    def test_unchecked_visual(self):
        d=self.base();d['objects'][0]['visual_status']='not_checked';self.assertEqual(check_manifest(d)['status'],'fail')
    def test_drawing_split(self):
        d=self.base();d['objects'][0].update(kind='drawing',whole_object_preserved=False,geometric_split=True,embedded_text_readability='pass');self.assertEqual(check_manifest(d)['status'],'fail')
    def test_table_missing_key(self):
        d=self.base();o=d['objects'][0];o.update(kind='table',source_cells=[{'row':0,'col':0,'text':'100'}],table_fragments=[{'header_repeated':True,'key_repeated':False,'cells':[{'row':0,'col':0,'text':'100'}]}]);self.assertEqual(check_manifest(d)['status'],'fail')
    def test_table_cell_changed(self):
        d=self.base();d['objects'][0].update(kind='table',source_cells=[{'row':0,'col':0,'text':'100'}],table_fragments=[{'header_repeated':True,'key_repeated':True,'cells':[{'row':0,'col':0,'text':'101'}]}]);self.assertEqual(check_manifest(d)['status'],'fail')
    def test_table_exact(self):
        d=self.base();d['objects'][0].update(kind='table',source_cells=[{'row':0,'col':0,'text':'100'}],table_fragments=[{'header_repeated':True,'key_repeated':True,'cells':[{'row':0,'col':0,'text':'100'}]}]);self.assertEqual(check_manifest(d)['status'],'pass')
    def test_output_mapping(self):
        d=self.base();d['output_page_count']=2;self.assertEqual(check_manifest(d)['status'],'fail')
if __name__=='__main__':unittest.main()
