#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""还原 VyH0 主库中 8 月全表匹配硬覆盖的字段。
保留来源关键词=婴儿车载摄像头任务关键词的记录；
清空来源关键词=足球任务 或 为空 的 7 个匹配字段；
CFC1 来源的记录留给下一步用 CFC1 画像重算。
"""
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

baby_car_keywords = {
    'amazon baby products','toddler gear',
    '5 Zoll 1080P Baby Auto Monitor','Baby Auto Monitor Rücksitz Test','Baby Autokamera Einbau & Auspacken',
    'Baby Autokamera Test','Baby Autokamera für rückwärtsgerichtete Sitze','Baby Autokamera mit Zoom & Spiegelmodus',
    'Baby Autokamera ohne WLAN','Baby Autositz Kamera Unboxing','Baby Reise Must Haves Auto','Erstausstattung Auto Baby',
    'Magnetische Baby Autokamera Unboxing','Nachtsicht Baby Autokamera Erfahrung','Roadtrip mit Baby Essentials',
    'Rücksitz Baby Monitor auspacken','beste Baby Autokamera 2026','magnetische Halterung Baby Autokamera',
    'rückwärtsgerichteter Kindersitz Kamera'
}
cfc1_keywords = {
    'AirTag passport holder review','AirTag travel accessories unboxing','best passport holder with AirTag tracking',
    'anti-theft travel wallet AirTag','business travel essentials 2025','minimalist travel passport wallet with AirTag',
    'AirTag hidden tracker wallet review','smart passport holder unboxing','magnetic wallet passport holder review',
    'travel influencer must-have gadgets','best AirTag passport holder 2025','best AirTag passport holder 2026',
    'international travel essentials AirTag'
}

CLEAR_FIELDS = ['匹配产品','匹配关键词','品牌匹配度','内容契合类型','开发优先级','推荐理由','匹配排序组']

def run(args):
    return wb.run(args)

def main():
    # 拉全表
    records = []
    off = 0
    while True:
        j = run(['base','+record-list','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--limit','200','--offset',str(off),'--format','json'])
        if not (j and j.get('ok')):
            print('LIST ERR', json.dumps(j, ensure_ascii=False)[:300]); break
        d = j['data']; rows = d.get('data',[]); flds = d.get('fields',[])
        if not rows: break
        if off == 0:
            print('字段:', flds)
        rids = d.get('record_id_list', [])
        ci = flds.index('来源关键词')
        for r, rid in zip(rows, rids):
            srcs = r[ci]
            if not isinstance(srcs, list): srcs = [srcs]
            srcs = [str(s or '').strip() for s in srcs]
            records.append({'rid': rid, 'srcs': srcs})
        if len(rows) < 200: break
        off += 200
    print('总记录:', len(records))

    # 分类
    keep = []      # 婴儿车来源，不动
    restore = []   # 足球/无来源，清空
    cfc1 = []      # CFC1来源，留给下一步
    for rec in records:
        srcs = rec['srcs']
        if any(s in baby_car_keywords for s in srcs):
            keep.append(rec)
        elif any(s in cfc1_keywords for s in srcs):
            cfc1.append(rec)
        else:
            restore.append(rec)

    print('保留(婴儿车):', len(keep))
    print('还原(足球/无来源):', len(restore))
    print('CFC1(下一步处理):', len(cfc1))

    # 构造清空更新
    clear_values = {}
    for f in CLEAR_FIELDS:
        clear_values[f] = None if f == '开发优先级' else ('' if f in ('匹配产品','匹配关键词','内容契合类型','推荐理由','匹配排序组') else None)
    # 品牌匹配度是 number, 清空用 None
    clear_values['品牌匹配度'] = None
    updates = {rec['rid']: clear_values.copy() for rec in restore}

    # 批量更新
    ok = 0; fail = 0
    items = list(updates.items())
    for i in range(0, len(items), 200):
        chunk = dict(items[i:i+200])
        j = run(['base','+record-batch-update','--as','user','--base-token',BASE_TOKEN,'--table-id',TABLE_ID,
                 '--format','json','--json', json.dumps({'update_records': chunk})])
        if j and j.get('ok'):
            ok += len(chunk)
            print(f'batch {i//200+1}: cleared {len(chunk)}')
        else:
            fail += len(chunk)
            print('BATCH FAIL:', json.dumps(j, ensure_ascii=False)[:500] if j else 'None')
    print(f'\n=== 还原完成: 成功 {ok} / 失败 {fail} ===')

if __name__ == '__main__':
    main()
