from pathlib import Path
import sys, tempfile, unittest
from pypdf import PdfWriter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_print_pdf import inspect_pdf
import workbench as w

class A3Tests(unittest.TestCase):
    def make(self,pages,rotation=0,crop=False):
        writer=PdfWriter()
        for width,height in pages:
            page=writer.add_blank_page(width=width*72/25.4,height=height*72/25.4)
            if rotation: page.rotate(rotation)
            if crop: page.cropbox.upper_right=(100,100)
        tmp=tempfile.NamedTemporaryFile(suffix='.pdf',delete=False)
        path=Path(tmp.name); tmp.close()
        with path.open('wb') as f: writer.write(f)
        self.addCleanup(path.unlink)
        return path
    def test_a3_landscape(self): self.assertEqual(inspect_pdf(self.make([(420,297)]))['status'],'pass')
    def test_a4_rejected(self): self.assertEqual(inspect_pdf(self.make([(297,210)]))['status'],'fail')
    def test_mixed_paper_rejected(self): self.assertEqual(inspect_pdf(self.make([(420,297),(297,210)]))['status'],'fail')
    def test_a3_portrait(self): self.assertEqual(inspect_pdf(self.make([(297,420)]),'portrait')['status'],'pass')
    def test_auto_rotation_rejected(self): self.assertEqual(inspect_pdf(self.make([(420,297)],90))['status'],'fail')
    def test_crop_mismatch_rejected(self): self.assertEqual(inspect_pdf(self.make([(420,297)],crop=True))['status'],'fail')
    def test_profile_configuration(self):
        d=w.load(w.ROOT/'config/layout_profiles.json')
        self.assertEqual(d['profiles']['print_a3']['canvas']['width_mm'],420)
        self.assertEqual(d['profiles']['print_a3']['font_pt']['body'],14)
        self.assertNotIn('print_a4',d['profiles'])
    def test_task_legacy_profile_rejected(self):
        task=w.load(w.ROOT/'templates/task.json'); task['requested_profiles']=['print_a4']
        with self.assertRaises(w.GateError): w.validate(task,'task')

if __name__=='__main__': unittest.main()
