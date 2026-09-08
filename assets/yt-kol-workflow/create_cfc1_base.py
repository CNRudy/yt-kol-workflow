#!/usr/bin/env python3
"""为 CFC1 (AirTag 护照包) 红人联系清单，新建一个独立飞书多维表格(Base)并写入 284 条数据。
基于 sync_to_user_base.py 的字段推断 + 批量写入逻辑，但只建一张表，且严格用 table_id 写入。
"""
import openpyxl, json, subprocess, sys, os, time, tempfile, re

LARK = "/Users/coscod/.workbuddy/binaries/node/versions/22.22.2/bin/lark-cli"
SRC_XLSX = "output/CFC1_contact_list.xlsx"
BASE_NAME = "CFC1 AirTag护照包红人库"
TABLE_NAME = "CFC1 红人联系清单"

# 显式设为单选（其余低基数列当 text，避免选项爆炸）
SELECT_COLS = {"国家/地区", "开发优先级", "邮箱状态", "亚马逊推广经验",
               "匹配产品", "来源关键词"}
URL_HINT = re.compile(r'url|链接', re.I)
DATE_HINT = re.compile(r'日期|时间|date|采集|发布', re.I)
NUM_HINT = re.compile(r'数|量|播放|订阅|互动|率|rate|count|粉丝|views|subs|价格|price', re.I)
# select 选项里要剔除的脏值
BAD_OPTS = {"", "?", "？", "未知", "N/A", "na", "none", "null", "-"}


def infer_type(col, vals):
    if URL_HINT.search(col):
        return "url"
    if DATE_HINT.search(col) and any(re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', str(v)) for v in vals[:30]):
        return "date"
    if NUM_HINT.search(col):
        num = sum(1 for v in vals if isinstance(v, (int, float)) or
                  (isinstance(v, str) and v.replace('.', '', 1).replace('-', '', 1).lstrip('+').isdigit()))
        if num >= len(vals) * 0.9:
            return "number"
    if col in SELECT_COLS:
        return "select"
    return "text"


def load_sheet(ws):
    rows = list(ws.iter_rows(values_only=True))
    hdr = list(rows[0])
    data = [r for r in rows[1:] if any(c is not None for c in r)]
    col_vals = {}
    for ci, col in enumerate(hdr):
        col_vals[col] = [r[ci] for r in data if ci < len(r) and r[ci] is not None]
    cols = [c for c in hdr if col_vals.get(c)]
    cols = [c for c in cols if c not in ("多行文本",)]
    specs, records = [], []
    for col in cols:
        vals = col_vals[col]
        t = infer_type(col, vals)
        if t == "select":
            opts = [{"name": str(v)} for v in sorted(
                {str(v).strip() for v in vals if str(v).strip() not in BAD_OPTS})][:100]
            specs.append({"type": "select", "name": col, "options": opts})
        elif t == "url":
            specs.append({"type": "text", "name": col, "style": {"type": "url"}})
        elif t == "date":
            specs.append({"type": "datetime", "name": col, "style": {"format": "yyyy-MM-dd HH:mm"}})
        elif t == "number":
            specs.append({"type": "number", "name": col})
        else:
            specs.append({"type": "text", "name": col})
    for r in data:
        row = {}
        ok = False
        for col in cols:
            ci = hdr.index(col)
            v = r[ci] if ci < len(r) else None
            if v is None or (isinstance(v, str) and v.strip() == ""):
                row[col] = None
                continue
            ok = True
            t = [s for s in specs if s["name"] == col][0]["type"]
            if t == "number":
                try:
                    row[col] = float(v) if ("." in str(v)) else int(v)
                except Exception:
                    row[col] = None
            else:
                row[col] = str(v)
        if ok:
            records.append(row)
    return cols, specs, records


def run(args, expect_ok=True):
    env = dict(os.environ)
    env["LARK_CLI_NO_PROXY_WARN"] = "1"
    p = subprocess.run([LARK] + args, capture_output=True, text=True, timeout=120,
                       cwd=os.getcwd(), env=env)
    raw = p.stdout.strip() or p.stderr.strip()
    if raw and not raw.startswith("{"):
        i = raw.find("{"); raw = raw[i:] if i >= 0 else raw
    try:
        j = json.loads(raw)
    except Exception:
        print("  ! 非JSON输出:", raw[:300], p.stderr[:200]); return None
    if expect_ok and not j.get("ok"):
        print("  ! lark-cli 失败:", json.dumps(j, ensure_ascii=False)[:400]); return None
    return j


def batch_write(base_token, table_id, cols, records, batch=200, pause=0.3):
    ok = fail = 0
    tmp = os.path.join(os.getcwd(), "._cfc1_batch_tmp.json")
    for i in range(0, len(records), batch):
        chunk = records[i:i + batch]
        rows = [[r.get(c) for c in cols] for r in chunk]
        body = {"fields": cols, "rows": rows}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        j = run(["base", "+record-batch-create", "--as", "user",
                 "--base-token", base_token, "--table-id", table_id,
                 "--json", "@._cfc1_batch_tmp.json", "--format", "json"], expect_ok=False)
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        if j and j.get("ok"):
            ok += len(chunk)
        else:
            fail += len(chunk)
            print(f"  ✗ 批次 {i//batch+1} 失败: {json.dumps(j, ensure_ascii=False)[:300]}")
        if pause:
            time.sleep(pause)
    return ok, fail


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", default=None, help="已有 base_token，跳过建 Base")
    ap.add_argument("--table-id", default=None, help="已有首表 table_id，跳过建 Base")
    args = ap.parse_args()

    if not os.path.exists(SRC_XLSX):
        print("源文件缺失:", SRC_XLSX); sys.exit(1)
    wb = openpyxl.load_workbook(SRC_XLSX, read_only=True, data_only=True)
    ws = wb.active
    cols, specs, records = load_sheet(ws)
    wb.close()
    print(f"[建 base] {BASE_NAME} + 表『{TABLE_NAME}』({len(cols)}字段, {len(records)}行)")
    print("  字段类型:")
    for s in specs:
        extra = f" 选项数={len(s.get('options',[]))}" if s.get("options") else ""
        print(f"    {s['name']:16} -> {s['type']}{extra}")

    base_token = args.base_token
    table_id = args.table_id
    if not (base_token and table_id):
        j = run(["base", "+base-create", "--as", "user", "--name", BASE_NAME,
             "--table-name", TABLE_NAME, "--fields", json.dumps(specs, ensure_ascii=False),
             "--format", "json"])
        if not j:
            print("建 base 失败，终止"); sys.exit(1)
        base_token = j["data"]["base"]["base_token"]
        url = j["data"]["base"]["url"]
        print(f"  base_token={base_token}\n  url={url}")
        jt = run(["base", "+table-list", "--as", "user", "--base-token", base_token, "--format", "json"])
        table_id = None
        if jt and jt.get("ok"):
            tables = jt["data"].get("tables") or jt["data"].get("items") or []
            for t in tables:
                if t.get("name") == TABLE_NAME or table_id is None:
                    table_id = t.get("table_id") or t.get("id")
        print(f"  首表 table_id={table_id}")
        if not table_id:
            print("  ! 无法获取 table_id，终止"); sys.exit(1)
    else:
        print(f"[复用已有 Base] base_token={base_token} table_id={table_id}")
        jt = run(["base", "+table-list", "--as", "user", "--base-token", base_token, "--format", "json"])
        if jt and jt.get("ok"):
            tables = jt["data"].get("tables") or jt["data"].get("items") or []
            for t in tables:
                if t.get("name") == TABLE_NAME:
                    table_id = t.get("table_id") or t.get("id")
            print(f"  确认首表 table_id={table_id}")

    ok, fail = batch_write(base_token, table_id, cols, records)
    print(f"  ✅ 『{TABLE_NAME}』写入 {ok}/{len(records)} (失败 {fail})")
    print(f"\n🎉 完成！Base 链接: https://pcn8zy4grswl.feishu.cn/base/{base_token}")
    print(f"   base_token={base_token}  table_id={table_id}")


if __name__ == "__main__":
    main()
