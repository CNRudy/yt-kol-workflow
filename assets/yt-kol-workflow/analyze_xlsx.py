import openpyxl, json, re
from collections import Counter

XLSX = "/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow/output/20260721_172846_batch/kol_summary_tables.xlsx"
wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

URL_HINT = re.compile(r'url|链接|link', re.I)
DATE_HINT = re.compile(r'日期|时间|date|采集|发布', re.I)
NUM_HINT = re.compile(r'数|量|播放|订阅|互动|rate|count|粉丝|views|subs|价格|price|万', re.I)

for ws in wb.worksheets:
    name = ws.title
    rows = list(ws.iter_rows(values_only=True))
    if not rows: 
        print(f"### {name}: EMPTY"); continue
    hdr = list(rows[0])
    data = [r for r in rows[1:] if any(c is not None for c in r)]
    print(f"\n### SHEET: {name}  (rows={len(data)}, cols={len(hdr)})")
    for ci, col in enumerate(hdr):
        vals = [r[ci] for r in data if ci < len(r) and r[ci] is not None]
        if not vals:
            print(f"  [{ci}] {col!r}: all-empty"); continue
        distinct = Counter(str(v) for v in vals)
        sample = str(vals[0])[:40]
        n_num = sum(1 for v in vals if isinstance(v,(int,float)) or (isinstance(v,str) and v.replace('.','',1).replace('-','',1).isdigit()))
        is_url = any(str(v).startswith('http') for v in vals[:20])
        is_date = any(re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', str(v)) for v in vals[:20])
        typ = 'text'
        if is_url: typ='url'
        elif is_date and DATE_HINT.search(str(col)): typ='date'
        elif n_num >= len(vals)*0.9 and NUM_HINT.search(str(col)): typ='number'
        elif len(distinct) <= 15: typ='select'
        extra = ''
        if typ=='select':
            extra = ' opts=' + ','.join(list(distinct)[:12])
        print(f"  [{ci}] {col!r:28} type={typ:7} distinct={len(distinct):3} sample={sample!r}{extra}")
