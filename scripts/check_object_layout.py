"""对象重排辅助门控：清单结构与一致性检查，不代替实际源/输出视觉验收。"""
from pathlib import Path
import json,argparse
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
def normalized(s):return ''.join(s.split())
def check_manifest(data):
    errors=[e.message for e in Draft202012Validator(json.loads((ROOT/'schemas/object_layout.schema.json').read_text())).iter_errors(data)]
    covered=set(); seen=set(); outpages=set(); expected_pages=set(range(1,data.get('output_page_count',0)+1))
    for o in data.get('objects',[]):
        ident=o.get('object_id','?')
        if ident in seen:errors.append('重复object_id: '+ident)
        seen.add(ident);covered.add(o.get('source_page'));outpages.update(o.get('output_pages',[]))
        if o.get('status')!='reflowed':errors.append(ident+':对象未完成')
        if o.get('visual_status')!='pass':errors.append(ident+':视觉未通过')
        if not o.get('evidence_refs'):errors.append(ident+':缺真实检查证据')
        minimum=o.get('measured_min_font_pt')
        if o.get('kind')=='paragraph':
            if normalized(o.get('source_text',''))!=normalized(o.get('output_text','')):errors.append(ident+':正文变化')
            if minimum is None or minimum<14:errors.append(ident+':正文字号不足或未测')
            if not o.get('whole_lines'):errors.append(ident+':文字被切割')
        elif o.get('kind')=='table':
            source=o.get('source_cells',[]); fragments=o.get('table_fragments',[]);cells={}
            if not source or not fragments:errors.append(ident+':无可靠源表或分页表')
            for fragment in fragments:
                if not fragment.get('header_repeated') or not fragment.get('key_repeated'):errors.append(ident+':缺重复表头/主键')
                for cell in fragment.get('cells',[]):
                    key=(cell['row'],cell['col']);value=cell['text']
                    if key in cells and cells[key]!=value:errors.append(ident+':跨页单元格冲突')
                    cells[key]=value
            expected={(c['row'],c['col']):c['text'] for c in source}
            if cells!=expected:errors.append(ident+':单元格缺失/改变/多出')
            if minimum is None or minimum<12:errors.append(ident+':表格字号不足或未测')
        elif o.get('kind') in ['drawing','image']:
            if not o.get('whole_object_preserved') or o.get('geometric_split'):errors.append(ident+':图对象被切割')
            if o.get('embedded_text_readability')!='pass':errors.append(ident+':内嵌文字可读性未通过')
    if covered!=set(range(1,data.get('source_page_count',0)+1)):errors.append('源页对象覆盖不完整')
    if outpages!=expected_pages:errors.append('输出页映射缺失或越界')
    return {'status':'fail' if errors else 'pass','errors':errors,'objects':len(seen),'source_pages':len(covered),'output_pages':len(outpages),'scope':'依赖上游真实数据与测量，不是自动视觉认证'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);a=p.parse_args()
    try:result=check_manifest(json.loads(Path(a.manifest).read_text(encoding='utf-8')))
    except (OSError,ValueError,KeyError,TypeError) as e:result={'status':'fail','errors':[str(e)]}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 2
if __name__=='__main__':raise SystemExit(main())
