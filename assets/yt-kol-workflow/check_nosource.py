#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 VyH0 主库中「来源关键词」为空/无来源的记录及其匹配字段现状。"""
import os
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')
os.environ['LARK_CLI_NO_PROXY_WARN'] = '1'

BASE_TOKEN = os.environ["FEISHU_BASE_TOKEN"]  # 从 .env / 环境变量读取，勿提交真实值
TABLE_ID  = 'tbl4rnFUM9jJXvCQ'

def run(args):
    return wb.run(args)

def main():
    records = []
    off = 0
    fields = None
    while True:
        j = run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--limit','200','--offset',str(off),'--format','json'])
        if not (j and j.get('ok')):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300]); break
        d = j['data']; rows = d.get('data',[]); flds = d.get('fields',[])
        if fields is None:
            fields = flds
            print('字段顺序:', fields)
        if not rows: break
        rids = d.get('record_id_list', [])
        for r, rid in zip(rows, rids):
            records.append((rid, r))
        if len(rows) < 200: break
        off += 200
    print('总记录:', len(records))

    ci_src = fields.index('来源关键词')
    ci_prod = fields.index('匹配产品') if '匹配产品' in fields else -1
    ci_score = fields.index('品牌匹配度') if '品牌匹配度' in fields else -1

    empty_src = []
    for rid, r in records:
        srcs = r[ci_src]
        if not isinstance(srcs, list): srcs = [srcs]
        srcs = [str(s or '').strip() for s in srcs]
        if not any(srcs):  # 空 / 无来源
            empty_src.append((rid, r, srcs))
    print('来源关键词为空/无来源 的记录数:', len(empty_src))

    # 这些无来源记录的匹配产品是否还残留
    if ci_prod >= 0:
        still_has_prod = [r for (_,r,_) in empty_src if r[ci_prod] not in (None,'',[],[''])]
        print('  其中「匹配产品」仍非空的数量:', len(still_has_prod))
    if ci_score >= 0:
        still_has_score = [r for (_,r,_) in empty_src if r[ci_score] not in (None,'',0)]
        print('  其中「品牌匹配度」仍非空的数量:', len(still_has_score))

    # 抽样打印前 10 条无来源记录的来源关键词原始值 + 匹配产品
    print('\n--- 无来源记录抽样(前10) ---')
    for rid, r, srcs in empty_src[:10]:
        prod = r[ci_prod] if ci_prod>=0 else '?'
        print(f'  {rid} | 来源={srcs} | 匹配产品={prod}')

if __name__ == '__main__':
    main()
