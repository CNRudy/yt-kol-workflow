#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反查 273 条「来源关键词为空」记录的爬取来源：
在所有 batch xlsx 里按 Channel ID 查找，从 per_keyword 目录名/文件名提取关键词。"""
import os
import sys, os, json, glob, re
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

def load_cids():
    records = []
    off = 0
    fields = None
    while True:
        j = run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--limit','200','--offset',str(off),'--format','json'])
        if not (j and j.get('ok')):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300]); break
        d = j['data']; rows = d.get('data',[]); flds = d.get('fields',[])
        if fields is None: fields = flds
        if not rows: break
        rids = d.get('record_id_list', [])
        ci = flds.index('来源关键词')
        ci_cid = flds.index('Channel ID')
        for r, rid in zip(rows, rids):
            srcs = r[ci]
            if not isinstance(srcs, list): srcs = [srcs]
            srcs = [str(s or '').strip() for s in srcs]
            if not any(srcs):
                records.append((rid, str(r[ci_cid] or '').strip()))
        if len(rows) < 200: break
        off += 200
    return records

def find_origin(target_cids):
    """遍历 output 下所有 xlsx，找 Channel ID 命中的文件，并从路径提取关键词。"""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    files = glob.glob(os.path.join(root, '**', '*.xlsx'), recursive=True)
    # 反向：cid -> 命中信息
    hit = {}  # cid -> list of (keyword, relpath)
    # 预编译关键词提取
    for fp in files:
        rel = os.path.relpath(fp, root)
        # 关键词来源：per_keyword/<kw>/ 目录，或文件名前缀 <date>_<kw>
        kw = None
        m = re.search(r'per_keyword[/_]([^/]+)[/_]', rel.replace('\\','/'))
        if m:
            kw = m.group(1)
        else:
            bn = os.path.basename(fp)
            # 形如 20260820_095734_best_AirTag_passport_holder_2026
            mm = re.match(r'\d{8}_\d{6}_(.+?)(?:\.xlsx)?$', bn)
            if mm:
                kw = mm.group(1)
        try:
            import openpyxl
            wbk = openpyxl.load_workbook(fp, read_only=True, data_only=True)
        except Exception as e:
            continue
        for ws in wbk.worksheets:
            rows = ws.iter_rows(values_only=True)
            try:
                header = next(rows)
            except StopIteration:
                continue
            # 找 Channel ID 列
            cid_idx = None
            for i,h in enumerate(header):
                if h and 'channel id' in str(h).lower():
                    cid_idx = i; break
            if cid_idx is None:
                continue
            for row in rows:
                if cid_idx >= len(row): continue
                val = row[cid_idx]
                if val is None: continue
                c = str(val).strip()
                if c in target_cids:
                    hit.setdefault(c, []).append((kw or '(文件名无关键词)', rel))
        try:
            wbk.close()
        except: pass
    return hit

def main():
    recs = load_cids()
    print('无来源记录数:', len(recs))
    cids = set(c for _,c in recs)
    print('唯一 Channel ID:', len(cids))
    with open('nosource_cids.json','w') as f:
        json.dump([{'rid':r,'cid':c} for r,c in recs], f, ensure_ascii=False, indent=2)
    print('已写出 nosource_cids.json')
    hit = find_origin(cids)
    found = set(hit.keys())
    notfound = cids - found
    print(f'\n在 output 批次文件命中: {len(found)} / {len(cids)}')
    print(f'未命中(可能非搜索批次导入): {len(notfound)}')
    # 关键词分布
    from collections import Counter
    kw_counter = Counter()
    for c, lst in hit.items():
        kws = set(k for k,_ in lst)
        for k in kws: kw_counter[k]+=1
    print('\n命中关键词分布(按出现记录数):')
    for k,v in kw_counter.most_common():
        print(f'  {v:4d}  {k}')

if __name__ == '__main__':
    main()
