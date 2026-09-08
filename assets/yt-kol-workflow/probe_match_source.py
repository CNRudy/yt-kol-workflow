#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探查 8 月全表匹配 Excel 结构，并统计 273 条无来源记录能在其中匹配多少。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openpyxl

root = os.path.dirname(os.path.abspath(__file__))
xlsx = os.path.join(root, 'output/us_baby_full_match/全表匹配_美国婴儿车载摄像头.xlsx')
wbk = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
ws = wbk.active
rows = ws.iter_rows(values_only=True)
header = next(rows)
print('总列数:', len(header))
print('表头:')
for i,h in enumerate(header):
    print(f'  [{i}] {h}')

# 找 Channel ID 列
cid_idx = None
for i,h in enumerate(header):
    if h and 'channel id' in str(h).lower():
        cid_idx = i; break
print('\nChannel ID 列索引:', cid_idx)

with open('nosource_cids.json') as f:
    recs = json.load(f)
cids = set(r['cid'] for r in recs)
print('无来源 cid 数:', len(cids))

matched = 0
sample = []
for row in rows:
    if cid_idx is None or cid_idx >= len(row): continue
    c = str(row[cid_idx] or '').strip()
    if c in cids:
        matched += 1
        if len(sample) < 3:
            sample.append(row)
print(f'\nExcel 中匹配到的无来源记录: {matched} / {len(cids)}')

# 打印匹配字段样例：找匹配产品/品牌匹配度/推荐理由/开发优先级/内容契合类型/匹配关键词/匹配排序组
def idx_of(names):
    for n in names:
        for i,h in enumerate(header):
            if h and n in str(h): return i
    return None
keys = ['匹配产品','品牌匹配度','推荐理由','开发优先级','内容契合类型','匹配关键词','匹配排序组']
print('\n样例(前3条匹配字段):')
for row in sample:
    d = {}
    for k in keys:
        j = idx_of([k])
        d[k] = row[j] if j is not None else 'N/A'
    print(' ', {k:(str(v)[:30] if v is not None else None) for k,v in d.items()})
