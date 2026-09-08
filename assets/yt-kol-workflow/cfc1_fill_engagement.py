#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 CFC1 飞书表补「代表视频互动率」列：从两批 batch 的 influencers_all.xlsx 按 Channel ID 回填。"""
import os
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
import openpyxl

wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'
BT = os.environ["FEISHU_BASE_TOKEN_CFC1"]  # 从 .env / 环境变量读取，勿提交真实值
TID = 'tblpAZFZ5KWywucp'
FIELD = '代表视频互动率'

def run(args):
    return wb.run(args)

def build_eng_map():
    m = {}
    for d in ['output/20260819_182645_batch', 'output/20260820_095734_batch']:
        wb_ = openpyxl.load_workbook(f'{d}/influencers_all.xlsx', read_only=True)
        ws = wb_.active
        rows = list(ws.iter_rows(values_only=True))
        hdr = rows[0]
        ci = hdr.index('Channel ID')
        ei = hdr.index('代表视频互动率')
        for r in rows[1:]:
            cid = str(r[ci] or '').strip()
            v = r[ei]
            if cid and v not in (None, ''):
                try:
                    m[cid] = float(v)
                except (ValueError, TypeError):
                    pass
        wb_.close()
    return m

def field_exists(name):
    j = run(['base', '+field-list', '--as', 'user', '--base-token', BT, '--table-id', TID, '--format', 'json'])
    if j and j.get('ok'):
        return any(f.get('name') == name for f in j['data'].get('fields', []))
    return False

def list_records():
    recs = []
    off = 0
    lim = 200
    while True:
        j = run(['base', '+record-list', '--as', 'user', '--base-token', BT, '--table-id', TID,
                 '--limit', str(lim), '--offset', str(off), '--format', 'json'])
        if not j or not j.get('ok'):
            break
        d = j['data']
        rows = d.get('data', [])
        flds = d.get('fields', [])
        rids = d.get('record_id_list', [])
        if not rows:
            break
        ci = flds.index('Channel ID')
        for i, row in enumerate(rows):
            rid = rids[i] if i < len(rids) else None
            cid = str(row[ci] if ci < len(row) else '').strip()
            recs.append((rid, cid))
        if len(rows) < lim:
            break
        off += lim
    return recs

def batch_update(upd):
    items = list(upd.items())
    done = 0
    for i in range(0, len(items), 200):
        chunk = items[i:i+200]
        u = {rid: {FIELD: val} for rid, val in chunk if val is not None}
        if not u:
            continue
        j = run(['base', '+record-batch-update', '--as', 'user', '--base-token', BT, '--table-id', TID,
                 '--format', 'json', '--json', json.dumps({'update_records': u})])
        if j and j.get('ok'):
            done += len(u)
            print(f'  批次 {i//200+1}: 更新 {len(u)} 条 ok')
        else:
            print(f'  批次 {i//200+1} ERR:', json.dumps(j, ensure_ascii=False)[:200] if j else 'None')
        time.sleep(0.3)
    return done

def main():
    eng = build_eng_map()
    print(f'互动率映射: {len(eng)} 条')

    if not field_exists(FIELD):
        j = run(['base', '+field-create', '--as', 'user', '--base-token', BT, '--table-id', TID,
                 '--format', 'json', '--json', json.dumps({'name': FIELD, 'type': 'number'})])
        print('FIELD-CREATE ok=', j.get('ok'))
        if not j.get('ok'):
            print('  ERR', json.dumps(j, ensure_ascii=False)[:300])
            return
    else:
        print('字段已存在，跳过创建')

    recs = list_records()
    print(f'飞书记录数: {len(recs)}')

    cid2rid = {}
    for rid, cid in recs:
        if cid:
            cid2rid.setdefault(cid, rid)

    upd = {}
    hit = 0
    miss = 0
    for cid, rid in cid2rid.items():
        if cid in eng:
            upd[rid] = eng[cid]
            hit += 1
        else:
            miss += 1
    print(f'可回填(命中本地互动率): {hit} | 无数据跳过: {miss}')

    done = batch_update(upd)
    print(f'实际更新: {done} 条')

    # 验证
    filled = 0
    off = 0
    while True:
        j = run(['base', '+record-list', '--as', 'user', '--base-token', BT, '--table-id', TID,
                 '--limit', '200', '--offset', str(off), '--format', 'json'])
        if not j or not j.get('ok'):
            break
        d = j['data']
        rows = d.get('data', [])
        flds = d.get('fields', [])
        if not rows:
            break
        idx = flds.index(FIELD)
        for row in rows:
            v = row[idx] if idx < len(row) else None
            if v not in (None, ''):
                filled += 1
        if len(rows) < 200:
            break
        off += 200
    print(f'验证: 代表视频互动率非空 = {filled} / {len(recs)}')

if __name__ == '__main__':
    main()
