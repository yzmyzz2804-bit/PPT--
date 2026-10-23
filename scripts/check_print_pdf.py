"""只读检查实际PDF是否为原生A3图幅；不保证视觉效果或打印机驱动设置。"""
import argparse
import json
from pathlib import Path
from pypdf import PdfReader

def inspect_pdf(path,orientation='landscape',tolerance_mm=1):
    reader=PdfReader(path)
    expected=(420,297) if orientation=='landscape' else (297,420)
    pages=[]
    for i,page in enumerate(reader.pages,1):
        unit=float(page.get('/UserUnit',1))
        rotation=int(page.get('/Rotate',0))%360
        boxes={}
        for name,box in [('media',page.mediabox),('crop',page.cropbox)]:
            size=[float(box.width)*unit*25.4/72,float(box.height)*unit*25.4/72]
            boxes[name]={'width_mm':round(size[0],3),'height_mm':round(size[1],3),'matches':all(abs(a-b)<=tolerance_mm for a,b in zip(size,expected))}
        passed=all(b['matches'] for b in boxes.values()) and rotation==0
        pages.append({'page':i,'rotation':rotation,'boxes':boxes,'status':'pass' if passed else 'fail'})
    return {'paper':'A3','orientation':orientation,'expected_mm':list(expected),'tolerance_mm':tolerance_mm,'page_count':len(pages),'status':'pass' if pages and all(p['status']=='pass' for p in pages) else 'fail','pages':pages,'scope':'仅PDF页面框与旋转检查；不证明字体、图像、视觉、实际驱动缩放或事实正确。'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--file',required=True)
    p.add_argument('--orientation',choices=['landscape','portrait'],default='landscape')
    p.add_argument('--output')
    args=p.parse_args()
    try:
        result=inspect_pdf(args.file,args.orientation)
    except Exception as e:
        result={'status':'error','error_type':type(e).__name__,'error':str(e)}
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        target=Path(args.output)
        if target.resolve()==Path(args.file).resolve():
            p.error('报告路径不能覆盖输入PDF')
        if target.exists(): p.error('报告已存在，请使用新版本文件名')
        if not target.parent.is_dir(): p.error('报告父目录不存在')
        target.write_text(payload+'\n',encoding='utf-8')
    print(payload)
    return 0 if result['status']=='pass' else 2

if __name__=='__main__': raise SystemExit(main())
