#!/usr/bin/env python3
"""用用户(你的)身份建一个你拥有的飞书多维表格 base，并把 4 张表数据全部写入。
这样你是 base 所有者，拥有字段配置和建视图的全部权限。
"""
import openpyxl, json, subprocess, sys, os, time, tempfile, re

LARK = "/Users/coscod/.workbuddy/binaries/node/versions/22.22.2/bin/lark-cli"
XLSX = "/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow/output/20260721_172846_batch/kol_summary_tables.xlsx"
BASE_NAME = "KOL网红开发工作流(可编辑版)"

# xlsx sheet标题 -> 飞书表名
SHEETS = {
    "influencers":      "网红详情表",
    "search_videos":    "视频数据表",
    "influencer_videos":"网红视频表",
    "search_tasks":     "搜索任务表",
}
# 首次建 base 时也想少建几张表？把飞书表名加进来即可，例如：
#   SKIP_TABLES = ["视频数据表", "网红视频表"]
# 当前：全建（用户决定暂不砍表，等碰到大表行数上限再开「网红视频表 2」）。
SKIP_TABLES = []
# 显式设为单选（其余低基数列当 text，避免选项爆炸）
SELECT_COLS = {
    "influencers": ["断更评估", "国家/地区", "邮箱状态", "邮箱来源",
                    "亚马逊推广经验", "开发状态", "来源关键词"],
}
URL_HINT = re.compile(r'url|链接', re.I)
DATE_HINT = re.compile(r'日期|时间|date|采集|发布', re.I)
NUM_HINT = re.compile(r'数|量|播放|订阅|互动|率|rate|count|粉丝|views|subs|价格|price', re.I)


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
    if col in SELECT_COLS.get(CUR_SHEET, []):
        return "select"
    return "text"


def load_sheet(ws):
    rows = list(ws.iter_rows(values_only=True))
    hdr = list(rows[0])
    data = [r for r in rows[1:] if any(c is not None for c in r)]
    # 收集每列非空值
    col_vals = {}
    for ci, col in enumerate(hdr):
        col_vals[col] = [r[ci] for r in data if ci < len(r) and r[ci] is not None]
    # 跳过全空列 & 已知垃圾列
    cols = [c for c in hdr if col_vals.get(c)]
    cols = [c for c in cols if c not in ("多行文本",)]
    specs, records = [], []
    for col in cols:
        vals = col_vals[col]
        t = infer_type(col, vals)
        if t == "select":
            opts = [{"name": str(v)} for v in sorted({str(v) for v in vals})][:100]
            specs.append({"type": "select", "name": col, "options": opts})
        elif t == "url":
            specs.append({"type": "text", "name": col, "style": {"type": "url"}})
        elif t == "date":
            specs.append({"type": "datetime", "name": col, "style": {"format": "yyyy-MM-dd HH:mm"}})
        elif t == "number":
            specs.append({"type": "number", "name": col})
        else:
            specs.append({"type": "text", "name": col})
    # 构造记录行
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
    p = subprocess.run([LARK] + args, capture_output=True, text=True, timeout=120)
    out = p.stdout.strip()
    try:
        j = json.loads(out)
    except Exception:
        print("  ! 非JSON输出:", out[:300], p.stderr[:200]); return None
    if expect_ok and not j.get("ok"):
        print("  ! lark-cli 失败:", json.dumps(j, ensure_ascii=False)[:400]); return None
    return j


def batch_write(base_token, table_name, cols, records, batch=200, pause=0.3):
    ok = fail = 0
    for i in range(0, len(records), batch):
        chunk = records[i:i + batch]
        rows = [[r.get(c) for c in cols] for r in chunk]
        body = {"fields": cols, "rows": rows}
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        j = run(["base", "+record-batch-create", "--as", "user",
                 "--base-token", base_token, "--table-id", table_name,
                 "--json", "@" + path, "--format", "json"], expect_ok=False)
        os.remove(path)
        if j and j.get("ok"):
            ok += len(chunk)
        else:
            fail += len(chunk)
            print(f"  ✗ 批次 {i//batch+1} 失败: {json.dumps(j, ensure_ascii=False)[:300]}")
            if fail > 0 and fail <= batch:  # 打印首条样例
                print("    样例:", json.dumps(rows[0], ensure_ascii=False)[:200])
        if pause:
            time.sleep(pause)
    return ok, fail


def main():
    global CUR_SHEET
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    # 先建 base + 第一张表(网红详情表)
    if "网红详情表" in SKIP_TABLES:
        print("『网红详情表』在 SKIP_TABLES 中，无法作为 base 首表，已中止。")
        sys.exit(1)
    CUR_SHEET = "influencers"
    ws = wb[CUR_SHEET]
    cols, specs, records = load_sheet(ws)
    print(f"[建 base] {BASE_NAME} + 表『网红详情表』({len(cols)}字段, {len(records)}行)")
    j = run(["base", "+base-create", "--as", "user", "--name", BASE_NAME,
             "--table-name", "网红详情表", "--fields", json.dumps(specs, ensure_ascii=False),
             "--format", "json"])
    if not j:
        print("建 base 失败，终止"); sys.exit(1)
    base_token = j["data"]["base"]["base_token"]
    url = j["data"]["base"]["url"]
    print(f"  base_token={base_token}\n  url={url}")
    ok, fail = batch_write(base_token, "网红详情表", cols, records)
    print(f"  ✅ 网红详情表 写入 {ok}/{len(records)} (失败 {fail})")

    # 其余 3 张表
    for sheet, tname in [("search_videos", "视频数据表"),
                         ("influencer_videos", "网红视频表"),
                         ("search_tasks", "搜索任务表")]:
        if tname in SKIP_TABLES:
            print(f"[跳过] 『{tname}』（已在 SKIP_TABLES 中，不创建）")
            continue
        CUR_SHEET = sheet
        ws = wb[sheet]
        cols, specs, records = load_sheet(ws)
        print(f"\n[建表] 『{tname}』({len(cols)}字段, {len(records)}行)")
        jt = run(["base", "+table-create", "--as", "user", "--base-token", base_token,
                  "--name", tname, "--fields", json.dumps(specs, ensure_ascii=False),
                  "--format", "json"])
        if not jt:
            print(f"  建表 {tname} 失败，跳过"); continue
        ok, fail = batch_write(base_token, tname, cols, records)
        print(f"  ✅ {tname} 写入 {ok}/{len(records)} (失败 {fail})")

    print(f"\n🎉 完成！base 链接: {url}")


if __name__ == "__main__":
    main()
