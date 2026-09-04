#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 VyH0 主库中全部 340 条 CFC1 红人重新用 CFC1 画像评分，覆盖错误的婴儿车/德语画像。"""
import os
import sys, os, json
from collections import OrderedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import write_user_base as wb
from filter.scoring import score_influencer
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

def load_profile():
    d = json.load(open('product_profiles.json'))
    return d['profiles']['airtag_passport_holder']

def to_float(v):
    try: return float(v)
    except: return 0.0

def clean_promo(v):
    s = str(v or '').strip()
    if not s or s == '未发现推广经验': return '未发现'
    return s

def clean_email_status(v):
    s = str(v or '').strip()
    return s if s else '需手动查找'

def clean_country(v):
    if v is None: return ''
    if isinstance(v, list):
        return str(v[0] or '').strip() if v else ''
    return str(v).strip()

def clean_activity(v):
    s = str(v or '').strip()
    if '断更' in s or '风险' in s: return '有断更风险'
    return '持续更新'

def run(args):
    return wb.run(args)

def main():
    profile = load_profile()
    print('CFC1 profile:', profile.get('name'))

    # 读取 batch 原始数据（取评分所需字段 + 同步字段）
    merged = OrderedDict()
    for path in BATCH_FILES:
        if not os.path.exists(path):
            print('跳过:', path); continue
        wb_xl = openpyxl.load_workbook(path, read_only=True)
        ws = wb_xl.active
        rows = list(ws.iter_rows(values_only=True))
        H = rows[0]; data = rows[1:]
        idx = {c: i for i, c in enumerate(H)}
        print(path, '行数:', len(data))
        for r in data:
            cid = str(r[idx.get('Channel ID')] or '').strip()
            if not cid: continue
            merged[cid] = {
                'channel_description': str(r[idx.get('频道描述')] or ''),
                'rep_video_title': str(r[idx.get('代表视频标题')] or ''),
                'rep_video_engagement': to_float(r[idx.get('代表视频互动率')]),
                'email_status': clean_email_status(r[idx.get('邮箱状态')]),
                'amazon_promo_level': clean_promo(r[idx.get('亚马逊推广经验')]),
                'country': clean_country(r[idx.get('国家/地区')]),
                'activity_status': clean_activity(r[idx.get('断更评估')]),
                'Channel Name': str(r[idx.get('Channel Name')] or '').strip() or None,
            }
        wb_xl.close()
    print('合并去重后:', len(merged))

    # 重算评分
    score_fields = ['匹配产品','品牌匹配度','内容契合类型','匹配关键词','开发优先级','推荐理由']
    updates = {}
    for cid, rec in merged.items():
        detail = {
            'channel_description': rec['channel_description'],
            'rep_video_title': rec['rep_video_title'],
            'rep_video_engagement': rec['rep_video_engagement'],
            'email_status': rec['email_status'],
            'amazon_promo_level': rec['amazon_promo_level'],
            'country': rec['country'],
            'activity_status': rec['activity_status'],
        }
        sc = score_influencer(detail, [], profile)
        updates[cid] = {
            '匹配产品': sc['match_profile'],
            '品牌匹配度': sc['brand_fit_score'],
            '内容契合类型': sc['content_types'] or '',
            '匹配关键词': sc['matched_keywords'] or '',
            '开发优先级': sc['dev_priority'],
            '推荐理由': sc['recommend_reason'],
        }
        if rec['Channel Name']:
            updates[cid]['Channel Name'] = rec['Channel Name']

    # 拉 VyH0 全表 Channel ID -> record_id
    cid2rid = {}
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
            if v: cid2rid[v] = rid
        if len(rows) < 200: break
        off += 200
    print('VyH0 映射:', len(cid2rid))

    # 过滤出存在的 340 条
    final_updates = {}
    missing = []
    for cid, vals in updates.items():
        if cid in cid2rid:
            final_updates[cid2rid[cid]] = vals
        else:
            missing.append(cid)
    print('可更新:', len(final_updates), '| VyH0 中找不到:', len(missing))

    # 批量更新
    ok = 0; fail = 0
    items = list(final_updates.items())
    for i in range(0, len(items), 200):
        chunk = dict(items[i:i+200])
        j = run(['base','+record-batch-update','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json', json.dumps({'update_records': chunk})])
        if j and j.get('ok'):
            ok += len(chunk)
            print(f'batch {i//200+1}: updated {len(chunk)}')
        else:
            fail += len(chunk)
            print('BATCH FAIL:', json.dumps(j, ensure_ascii=False)[:500] if j else 'None')
    print(f'\n=== 完成: 更新 {ok} / 失败 {fail} ===')

if __name__ == '__main__':
    main()
