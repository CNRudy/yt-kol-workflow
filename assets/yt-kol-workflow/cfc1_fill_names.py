#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 CFC1 飞书表补回「频道名称」列：按 Channel ID 关联本地 batch 真名回填。"""
import os
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb

wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'

BT = os.environ["FEISHU_BASE_TOKEN_CFC1"]  # 从 .env / 环境变量读取，勿提交真实值
TID = 'tblpAZFZ5KWywucp'
NAME_MAP_PATH = 'output/cfc1_name_fix/name_map.json'

def run(args):
    return wb.run(args)

def list_all_records():
    """分页拉取全表，返回 list of (record_id, channel_id)。"""
    records = []
    offset = 0
    limit = 200
    while True:
        j = run(['base', '+record-list', '--as', 'user', '--base-token', BT,
                 '--table-id', TID, '--limit', str(limit), '--offset', str(offset),
                 '--format', 'json'])
        if not j or not j.get('ok'):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300] if j else 'None')
            break
        d = j.get('data', {})
        rows = d.get('data', [])
        fields = d.get('fields', [])
        rid_list = d.get('record_id_list', [])
        if not rows:
            break
        try:
            ch_idx = fields.index('Channel ID')
        except ValueError:
            print('NO Channel ID col in', fields)
            break
        for i, row in enumerate(rows):
            rid = rid_list[i] if i < len(rid_list) else (row[-1] if row else None)
            cid = str(row[ch_idx] if ch_idx < len(row) else '').strip()
            records.append((rid, cid))
        if len(rows) < limit:
            break
        offset += limit
    return records

def batch_update(mapping):
    """mapping: dict record_id -> channel_name。分批 200 更新。"""
    items = list(mapping.items())
    total = len(items)
    done = 0
    for i in range(0, total, 200):
        chunk = items[i:i+200]
        upd = {rid: {"频道名称": name} for rid, name in chunk if name}
        if not upd:
            continue
        j = run(['base', '+record-batch-update', '--as', 'user', '--base-token', BT,
                 '--table-id', TID, '--format', 'json', '--json', json.dumps({"update_records": upd})])
        if j and j.get('ok'):
            done += len(upd)
            print(f'  批次 {i//200+1}: 更新 {len(upd)} 条 ok')
        else:
            print(f'  批次 {i//200+1} ERR:', json.dumps(j, ensure_ascii=False)[:300] if j else 'None')
        time.sleep(0.5)
    return done

def main():
    # 读取本地名字映射
    with open(NAME_MAP_PATH, encoding='utf-8') as f:
        name_map = json.load(f)  # channel_id -> {channel_name, kol_name}
    print(f'本地名字映射: {len(name_map)} 条')

    # 拉全表
    print('拉取 CFC1 全表记录...')
    recs = list_all_records()
    print(f'  飞书记录数: {len(recs)}')

    # 建 channel_id -> record_id
    cid2rid = {}
    for rid, cid in recs:
        if cid:
            cid2rid.setdefault(cid, rid)

    # 组装更新映射
    upd_map = {}
    hit = 0
    miss = 0
    for cid, rid in cid2rid.items():
        info = name_map.get(cid)
        if info and info.get('channel_name'):
            upd_map[rid] = info['channel_name']
            hit += 1
        else:
            miss += 1
    print(f'  可回填(命中本地名字): {hit} | 无名字跳过: {miss}')

    # 执行更新
    print('回写「频道名称」列...')
    done = batch_update(upd_map)
    print(f'  实际更新: {done} 条')

    # 验证：回拉统计非空
    print('验证写入结果...')
    filled = 0
    offset = 0
    while True:
        j = run(['base', '+record-list', '--as', 'user', '--base-token', BT,
                 '--table-id', TID, '--limit', '200', '--offset', str(offset), '--format', 'json'])
        if not j or not j.get('ok'):
            break
        d = j.get('data', {})
        rows = d.get('data', [])
        fields = d.get('fields', [])
        if not rows:
            break
        try:
            idx = fields.index('频道名称')
        except ValueError:
            print('频道名称列未找到'); break
        for row in rows:
            v = row[idx] if idx < len(row) else None
            if str(v or '').strip():
                filled += 1
        if len(rows) < 200:
            break
        offset += 200
    print(f'  验证: 频道名称非空 = {filled} / {len(recs)}')

if __name__ == '__main__':
    main()
