#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')
os.environ['LARK_CLI_NO_PROXY_WARN'] = '1'
BASE_TOKEN=os.environ["FEISHU_BASE_TOKEN"]  # 从 .env / 环境变量读取，勿提交真实值
TABLE_ID='tbl4rnFUM9jJXvCQ'
def run(a): return wb.run(a)

with open('nosource_cids.json') as f:
    recs=json.load(f)
target_rids=set(r['rid'] for r in recs)

# 全表统计
records=[]; off=0; fields=None
while True:
    j=run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,'--limit','200','--offset',str(off),'--format','json'])
    if not(j and j.get('ok')): break
    d=j['data']; rows=d.get('data',[]); flds=d.get('fields',[])
    if fields is None: fields=flds
    if not rows: break
    rids=d.get('record_id_list',[])
    for r,rid in zip(rows,rids): records.append((rid,r))
    if len(rows)<200: break
    off+=200

ci_p=fields.index('匹配产品'); ci_s=fields.index('来源关键词'); ci_sc=fields.index('品牌匹配度'); ci_pr=fields.index('开发优先级')
from collections import Counter
prod_counter=Counter()
no_src=0; no_prod=0; checked=0
samples=[]
for rid,r in records:
    p=r[ci_p]; s=r[ci_s]
    prod_counter[str(p) if p not in (None,'',[],['']) else '(空)']+=1
    if rid in target_rids:
        checked+=1
        ss=s if isinstance(s,list) else [s]
        if not any(str(x or '').strip() for x in ss): no_src+=1
        if p in (None,'',[],['']): no_prod+=1
        if len(samples)<5:
            samples.append((rid, str(p), str(s), str(r[ci_sc]), str(r[ci_pr])))
print('全表记录:',len(records))
print('匹配产品分布:', dict(prod_counter))
print(f'\n目标 273 条中已验证: {checked}')
print(f'  来源关键词仍为空: {no_src}')
print(f'  匹配产品仍为空: {no_prod}')
print('\n抽样(rid | 匹配产品 | 来源关键词 | 品牌匹配度 | 开发优先级):')
for s in samples: print('  ', s)
