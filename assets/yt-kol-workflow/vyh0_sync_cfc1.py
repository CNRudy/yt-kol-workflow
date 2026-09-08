#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 CFC1 独立 Base 的 340 位红人同步到 VyH0 主库网红详情表。
- 已存在 VyH0 的 284 条：更新核心字段（含 CFC1 画像评分）
- 不存在的 56 条：插入新记录
"""
import os
import sys, os, json
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
wb.LARK = '/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli'
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7890')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7890')
os.environ['LARK_CLI_NO_PROXY_WARN'] = '1'

import openpyxl

BASE_TOKEN = os.environ["FEISHU_BASE_TOKEN"]  # 从 .env / 环境变量读取，勿提交真实值
TABLE_ID  = 'tbl4rnFUM9jJXvCQ'

BATCH_FILES = [
    'output/20260819_182645_batch/influencers_all.xlsx',
    'output/20260820_095734_batch/influencers_all.xlsx',
    'output/20260903_164859_batch/influencers_all.xlsx',
]

# 字段映射: batch列名 -> VyH0字段名
FIELD_MAP = {
    'Channel ID': 'Channel ID',
    'Channel Name': 'Channel Name',
    '频道URL': '频道URL',
    '订阅数': '订阅数',
    '国家/地区': '国家/地区',
    '联系邮箱': '联系邮箱',
    '候选邮箱': '候选邮箱',
    '邮箱状态': '邮箱状态',
    '亚马逊推广经验': '亚马逊推广经验',
    'Amazon带货视频数': 'Amazon带货视频数',
    'Amazon Storefront': 'Amazon Storefront',
    '推广证据': '推广证据',
    '代表视频URL': '代表视频URL',
    '代表视频互动率': '代表视频互动率',
    '代表视频标题': '代表视频标题',
    '来源关键词': '来源关键词',
    '匹配产品': '匹配产品',
    '品牌匹配度': '品牌匹配度',
    '内容契合类型': '内容契合类型',
    '匹配关键词': '匹配关键词',
    '开发优先级': '开发优先级',
    '推荐理由': '推荐理由',
}

def to_int(v):
    try:
        return int(float(v))
    except Exception:
        return None

def to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def clean_select(v):
    if v is None: return None
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return s if s else None

def run(args):
    return wb.run(args)

def load_batches():
    merged = OrderedDict()
    for path in BATCH_FILES:
        if not os.path.exists(path):
            print('跳过不存在:', path); continue
        wb_xl = openpyxl.load_workbook(path, read_only=True)
        ws = wb_xl.active
        rows = list(ws.iter_rows(values_only=True))
        H = rows[0]; data = rows[1:]
        idx = {c: i for i, c in enumerate(H)}
        print(path, '行数:', len(data))
        for r in data:
            cid = str(r[idx.get('Channel ID')] or '').strip()
            if not cid: continue
            rec = {}
            for src, dst in FIELD_MAP.items():
                val = r[idx.get(src)] if idx.get(src) is not None else None
                if dst in ('订阅数','Amazon带货视频数'):
                    val = to_int(val)
                elif dst == '品牌匹配度':
                    val = to_int(val)
                elif dst == '代表视频互动率':
                    val = to_float(val)
                elif dst in ('国家/地区','邮箱状态','亚马逊推广经验','来源关键词','匹配产品','开发优先级'):
                    val = clean_select(val)
                else:
                    val = str(val).strip() if val is not None else None
                    if val == '': val = None
                rec[dst] = val
            merged[cid] = rec
        wb_xl.close()
    print('合并去重后:', len(merged))
    return merged

def main():
    cfc1_records = load_batches()

    # 拉 VyH0 全表 Channel ID -> record_id
    vyh0_cid2rid = {}
    off = 0
    while True:
        j = run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--limit','200','--offset',str(off),'--format','json'])
        if not (j and j.get('ok')):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300]); break
        d = j['data']; rows = d.get('data',[]); flds = d.get('fields',[])
        if not rows: break
        ci = flds.index('Channel ID')
        for r, rid in zip(rows, d.get('record_id_list', [])):
            v = str(r[ci] or '').strip()
            if v: vyh0_cid2rid[v] = rid
        if len(rows) < 200: break
        off += 200
    print('VyH0 现有记录:', len(vyh0_cid2rid))

    # 补全国家/地区选项（如 MY）避免 create 报 not_found
    fl = run(['base','+field-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,'--format','json'])
    country_field = next((f for f in fl['data']['fields'] if f['name'] == '国家/地区'), None)
    if country_field:
        countries = set()
        for rec in cfc1_records.values():
            v = rec.get('国家/地区')
            if isinstance(v, list): countries.update(v)
            elif v: countries.add(v)
        existing = {o['name'] for o in country_field.get('options', [])}
        missing = sorted(countries - existing)
        if missing:
            print('需补 国家/地区 选项:', missing)
            new_opts = country_field.get('options', []) + [{'name': c} for c in missing]
            up = run(['base','+field-update','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                      '--field-id', country_field['id'], '--format','json','--yes',
                      '--json', json.dumps({'name': country_field['name'], 'type': country_field['type'],
                                            'multiple': country_field.get('multiple', False),
                                            'options': new_opts})])
            print('field-update ok=', (up or {}).get('ok'), (up or {}).get('msg',''))

    update_recs = []
    create_recs = []
    for cid, rec in cfc1_records.items():
        rec.pop('匹配排序组', None)  # 不写入
        if cid in vyh0_cid2rid:
            rec['__rid'] = vyh0_cid2rid[cid]
            update_recs.append(rec)
        else:
            create_recs.append(rec)
    print('需要更新:', len(update_recs), '| 需要新增:', len(create_recs))

    # 批量更新
    updated = 0
    for i in range(0, len(update_recs), 200):
        chunk = update_recs[i:i+200]
        payload = {rec.pop('__rid'): {k:v for k,v in rec.items() if v is not None} for rec in chunk}
        j = run(['base','+record-batch-update','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json', json.dumps({'update_records': payload})])
        if j and j.get('ok'):
            updated += len(chunk)
            print(f'update batch {i//200+1}: {len(chunk)}')
        else:
            print('UPDATE FAIL:', json.dumps(j, ensure_ascii=False)[:500] if j else 'None')

    # 批量创建
    created = 0
    fields = list(FIELD_MAP.values())
    for i in range(0, len(create_recs), 200):
        chunk = create_recs[i:i+200]
        matrix = []
        for rec in chunk:
            matrix.append([rec.get(f) for f in fields])
        j = run(['base','+record-batch-create','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json', json.dumps({'fields': fields, 'rows': matrix})])
        if j and j.get('ok'):
            created += len(chunk)
            print(f'create batch {i//200+1}: {len(chunk)}')
        else:
            print('CREATE FAIL:', json.dumps(j, ensure_ascii=False)[:500] if j else 'None')

    print(f'\n=== 完成: 更新 {updated} / 新增 {created} ===')

if __name__ == '__main__':
    main()
