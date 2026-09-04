#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 CFC1 飞书表新增的 56 位红人加带颜色的「数据标记」列(红色=新增, 灰色=存量)。"""
import os
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')
os.environ['LARK_CLI_NO_PROXY_WARN'] = '1'

BASE_TOKEN = os.environ["FEISHU_BASE_TOKEN_CFC1"]  # 从 .env / 环境变量读取，勿提交真实值
TABLE_ID  = 'tblpAZFZ5KWywucp'
NEW_FILE  = 'output/cfc1_name_fix/new_56_cids.json'
MARK_FIELD = '数据标记'
NEW_LABEL  = '🆕 新增 09-03'
OLD_LABEL  = '存量'

def run(args):
    return wb.run(args)

def main():
    # 0) 先检查「数据标记」列是否已存在(幂等)
    fl = run(['base','+field-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,'--format','json'])
    existing_names = {f.get('name') for f in (fl or {}).get('data', {}).get('fields', [])}
    if MARK_FIELD in existing_names:
        print('「数据标记」列已存在，跳过建列')
    else:
        # 1) 建「数据标记」单选列(带颜色)
        j = run(['base','+field-create','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json',
                 json.dumps({'name': MARK_FIELD, 'type': 'select',
                             'options': [
                                 {'name': NEW_LABEL, 'hue': 'Red', 'lightness': 'Standard'},
                                 {'name': OLD_LABEL, 'hue': 'Gray', 'lightness': 'Standard'},
                             ]})])
        print('FIELD-CREATE ok=', (j or {}).get('ok'), (j or {}).get('msg',''))
        if not (j and j.get('ok')):
            print('  field-create 失败，退出'); return
        else:
            print('  已建列：', MARK_FIELD)

    # 2) 拉全表 Channel ID -> record_id 映射
    cid2rid = {}
    total = 0
    offset = 0
    limit = 200
    ch_idx = None
    while True:
        j = run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--limit',str(limit),'--offset',str(offset),'--format','json'])
        if not (j and j.get('ok')):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300]); break
        d = j['data']; rows = d.get('data', []); flds = d.get('fields', [])
        if ch_idx is None:
            ch_idx = flds.index('Channel ID')
        if not rows: break
        for r, rid in zip(rows, d.get('record_id_list', [])):
            total += 1
            v = str(r[ch_idx] or '').strip()
            if v: cid2rid[v] = rid
        if len(rows) < limit: break
        offset += limit
    print('全表记录:', total, '| 映射:', len(cid2rid))

    # 3) 读新增 56 个 Channel ID
    new = json.load(open(NEW_FILE))
    new_cids = {c for c, _ in new}
    print('新增 Channel ID 数:', len(new_cids))

    # 4) 构造更新: 新增->Red, 其余->Gray
    updates = {}
    matched_new = 0
    for cid, rid in cid2rid.items():
        if cid in new_cids:
            updates[rid] = {MARK_FIELD: NEW_LABEL}
            matched_new += 1
        else:
            updates[rid] = {MARK_FIELD: OLD_LABEL}
    print('匹配到新增记录:', matched_new, '| 将标记存量:', len(cid2rid) - matched_new)

    # 5) 批量更新(每批<=200, 用 record-batch-update)
    ok_total = 0
    fail = 0
    items = list(updates.items())
    for i in range(0, len(items), 200):
        chunk = dict(items[i:i+200])
        j = run(['base','+record-batch-update','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json', json.dumps({'update_records': chunk})])
        if j and j.get('ok'):
            ok_total += len(chunk)
            print(f'batch {i//200+1}: updated {len(chunk)}')
        else:
            fail += len(chunk)
            print('BATCH FAIL:', json.dumps(j, ensure_ascii=False)[:500] if j else 'None')
    print(f'\n=== 完成: 更新成功 {ok_total} / 失败 {fail} ===')

if __name__ == '__main__':
    main()
