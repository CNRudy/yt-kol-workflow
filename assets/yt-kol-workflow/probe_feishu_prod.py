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

seen=set(); srcset=set()
off=0
while True:
    j=run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,'--limit','200','--offset',str(off),'--format','json'])
    if not(j and j.get('ok')): break
    d=j['data']; rows=d.get('data',[]); fields=d.get('fields',[])
    if not rows: break
    ci_p=fields.index('匹配产品'); ci_s=fields.index('来源关键词')
    for r in rows:
        p=r[ci_p]
        if p not in (None,'',[],['']): seen.add(str(p))
        s=r[ci_s]
        ss = s if isinstance(s,list) else [s]
        for x in ss:
            if x not in (None,'',[]): srcset.add(str(x))
    if len(rows)<200: break
    off+=200
print('匹配产品现有值集合:', sorted(seen))
print('来源关键词现有值集合:', sorted(srcset))
