#!/usr/bin/env python3
"""Robust direct sync of KOL workbook -> Feishu Bitable (App/tenant mode).

Field-type notes discovered against Feishu API:
  * add_field response is data.field.field_id (nested)
  * date (type 5) value must be a BARE integer unix-ms timestamp (not {"timestamp":..})
  * url  (type 15) value is {"text": s, "link": s}
  * single_select options can only be embedded at field-creation time
    (PATCH/POST options -> 404), so we store those columns as plain text
Usage:
  python feishu_sync_v2.py                 # sync all 4 datasets
  python feishu_sync_v2.py --sheet influencers
  python feishu_sync_v2.py --reset        # clear target tables before writing
"""
import argparse, requests, openpyxl, time, os
from datetime import datetime, timezone

# 凭据从环境变量读取（.env 示例见 assets/yt-kol-workflow/.env.example），勿提交真实值
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE = os.environ.get("FEISHU_BASE_TOKEN", "")
TBL_INFL = "tbl1opmlkmE3veas"
XLSX = "/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow/output/20260721_172846_batch/kol_summary_tables.xlsx"
API = "https://open.feishu.cn/open-apis"

# (column, feishu_type)  1=text 2=number 5=date 15=url
T_INFL = [
    ("Channel ID",1),("Channel Name",1),("KOL Name",1),("网红记录日期",5),
    ("最新发布日期",5),("断更评估",1),("频道URL",15),("订阅数",2),
    ("频道总播放量",2),("视频总数",2),("国家/地区",1),("频道创建日期",5),
    ("频道描述",1),("频道初步判断",1),("联系邮箱",1),("邮箱状态",1),
    ("代表视频URL",15),("代表视频标题",1),("代表视频播放量",2),
    ("代表视频互动率",2),("来源关键词",1),("开发状态",1),("开发负责人",1),
    ("备注",1),("多行文本",1),
]
T_VIDS = [
    ("多行文本",1),("搜索关键词",1),("视频URL",15),("视频记录日期",5),
    ("Video ID",1),("Channel ID",1),("Channel Name",1),("Video Title",1),
    ("Publish Time",5),("Views",2),("Likes",2),("Comments",2),("互动率(%)",2),
    ("Duration (sec)",2),("Duration (H:M:S)",1),("Tags",1),("Has Subtitles",1),
    ("是否通过筛选",1),("筛选原因",1),("唯一键",1),
]
T_IVIDS = [
    ("多行文本",1),("Channel ID",1),("Channel Name",1),("视频URL",15),
    ("Video ID",1),("Video Title",1),("Publish Time",5),("Views",2),("Likes",2),
    ("Comments",2),("互动率(%)",2),("Duration (sec)",2),("Duration (H:M:S)",1),
    ("Tags",1),("字幕内容",1),("唯一键",1),
]
T_TASKS = [
    ("多行文本",1),("搜索关键词",1),("排序策略",1),("地区",1),("搜索时间",5),
    ("搜索结果数",2),("筛选通过数",2),("独立频道数",2),("新增网红数",2),
    ("配额消耗",2),("执行状态",1),("备注",1),("唯一键",1),
]

# columns in the influencers table that currently exist as single_select
# and must be dropped/recreated as text
INF_RECREATE_AS_TEXT = ["断更评估", "邮箱状态", "开发状态"]
# empty template leftover fields auto-created with the base
INF_TEMPLATE_LEFTOPVERS = ["文本", "单选", "日期", "附件"]


def to_ts_ms(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        dt = v
    else:
        s = str(v).strip().replace("Z", "+00:00")
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d",
                    "%Y-%m-%d", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(s, fmt); break
            except ValueError:
                continue
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def to_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def looks_url(v):
    return isinstance(v, str) and v.strip().lower().startswith(("http://", "https://"))


class FS:
    def __init__(self):
        self.token = self._tok()
        self.H = {"Authorization": f"Bearer {self.token}",
                  "Content-Type": "application/json; charset=utf-8"}

    def _tok(self):
        r = requests.post(f"{API}/auth/v3/tenant_access_token/internal",
                          json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=20)
        return r.json()["tenant_access_token"]

    def _req(self, method, path, body=None, params=None):
        for _ in range(3):
            r = requests.request(method, f"{API}{path}", headers=self.H,
                                 json=body, params=params, timeout=60)
            try:
                j = r.json()
            except Exception:
                j = {}
            if j.get("code") == 99991663:
                self.token = self._tok()
                self.H["Authorization"] = f"Bearer {self.token}"
                continue
            return j
        return j

    def list_tables(self):
        return {t["name"]: t["table_id"] for t in
                self._req("GET", f"/bitable/v1/apps/{BASE}/tables").get("data", {}).get("items", [])}

    def create_table(self, name):
        return self._req("POST", f"/bitable/v1/apps/{BASE}/tables",
                         body={"table": {"name": name}}).get("data", {}).get("table_id")

    def list_fields(self, tid):
        return {f["field_name"]: f for f in
                self._req("GET", f"/bitable/v1/apps/{BASE}/tables/{tid}/fields").get("data", {}).get("items", [])}

    def add_field(self, tid, name, ftype):
        j = self._req("POST", f"/bitable/v1/apps/{BASE}/tables/{tid}/fields",
                      body={"field_name": name, "type": ftype})
        return j.get("data", {}).get("field", {}).get("field_id")

    def del_field(self, tid, fid):
        return self._req("DELETE", f"/bitable/v1/apps/{BASE}/tables/{tid}/fields/{fid}")

    def list_records(self, tid):
        return self._req("GET", f"/bitable/v1/apps/{BASE}/tables/{tid}/records",
                         params={"page_size": 1}).get("data", {}).get("total", 0)

    def fetch_all_ids(self, tid):
        # Chain the REAL cursor (page_token is an opaque string, NOT a page number).
        ids = []
        page_token = None
        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            j = self._req("GET", f"/bitable/v1/apps/{BASE}/tables/{tid}/records", params=params)
            data = j.get("data", {}) or {}
            ids += [r["record_id"] for r in data.get("items", [])]
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break
        return ids

    def delete_all(self, tid):
        # Robust purge: keep fetching+deleting until two consecutive clean reads
        # return no records (defeats the transient "0 records" right after a write).
        total_deleted = 0
        for _ in range(8):
            ids = self.fetch_all_ids(tid)
            if not ids:
                time.sleep(0.4)
                if not self.fetch_all_ids(tid):
                    break
                continue
            for i in range(0, len(ids), 100):
                self._req("POST", f"/bitable/v1/apps/{BASE}/tables/{tid}/records/batch_delete",
                          body={"records": ids[i:i+100]})
            total_deleted += len(ids)
            time.sleep(0.3)
        if total_deleted:
            print(f"  🗑 清空 {total_deleted} 条旧记录")
        return total_deleted

    def batch_create(self, tid, records):
        return self._req("POST", f"/bitable/v1/apps/{BASE}/tables/{tid}/records/batch_create",
                         body={"records": records})


def ensure_fields(fs, tid, schema, recreate_text=None, drop_template=None):
    recreate_text = recreate_text or []
    drop_template = drop_template or []
    fields = fs.list_fields(tid)
    # drop template leftovers (empty)
    for name in drop_template:
        if name in fields:
            fs.del_field(tid, fields[name]["field_id"])
            print(f"  - 删除模板遗留字段 {name!r}")
    # recreate single_select as text
    for name in recreate_text:
        if name in fields and fields[name]["type"] == 3:
            fs.del_field(tid, fields[name]["field_id"])
            print(f"  - 将单选字段 {name!r} 改为文本")
    # re-read, then add missing
    fields = fs.list_fields(tid)
    names = set(fields.keys())
    for col, ftype in schema:
        if col not in names:
            fid = fs.add_field(tid, col, ftype)
            fields[col] = {"field_id": fid, "type": ftype}
            print(f"  + 新增字段 {col!r} type={ftype}")
    # final authoritative map
    fields = fs.list_fields(tid)
    return {c: (fields[c]["field_id"], fields[c]["type"]) for c, _ in schema if c in fields}


def convert(ftype, v):
    if v is None or v == "":
        return None
    if ftype == 2:
        n = to_num(v)
        return n
    if ftype == 15:
        return {"text": str(v).strip(), "link": str(v).strip()} if looks_url(v) else None
    if ftype == 5:
        return to_ts_ms(v)
    return str(v)


def sync(fs, sheet, tid, schema, recreate_text, drop_template, reset, batch_size=100, pause=0.0):
    print(f"\n========== {sheet} -> {tid} ==========")
    existing = fs.list_records(tid)
    if existing and not reset:
        print(f"  ⚠️ 数据表已有 {existing} 条记录，跳过写入（用 --reset 可清空重写）")
        return 0, 0
    if reset:
        fs.delete_all(tid)
    meta = ensure_fields(fs, tid, schema, recreate_text, drop_template)

    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = list(rows[0])
    data = [dict(zip(header, r)) for r in rows[1:]]
    print(f"  Excel 行数: {len(data)}; 可用字段: {len(meta)}/{len(schema)}")

    records, skipped = [], 0
    for r in data:
        fields = {}
        for col, (fid, ftype) in meta.items():
            if col not in header:
                continue
            val = convert(ftype, r.get(col))
            if val is None:
                continue
            fields[col] = val
        if fields:
            records.append({"fields": fields})
        else:
            skipped += 1

    print(f"  待写入: {len(records)} (空行跳过 {skipped})")
    ok = fail = 0
    n = max(1, batch_size)
    for i in range(0, len(records), n):
        batch = records[i:i+n]
        j = fs.batch_create(tid, batch)
        if j.get("code") == 0:
            ok += len(batch)
        else:
            fail += len(batch)
            print(f"  ✗ 批次 {i//n+1} 失败 code={j.get('code')} msg={j.get('msg')}")
            print("    样例:", str(batch[0])[:200])
        if pause:
            time.sleep(pause)
    print(f"  ✅ 写入完毕: 成功 {ok} / 失败 {fail}")
    # Verify actual stored count matches what we intended to write.
    time.sleep(0.5)
    real = 0
    pt = None
    while True:
        pr = {"page_size": 100}
        if pt:
            pr["page_token"] = pt
        jj = fs._req("GET", f"/bitable/v1/apps/{BASE}/tables/{tid}/records", params=pr)
        dd = jj.get("data", {}) or {}
        real += len(dd.get("items", []))
        if not dd.get("has_more"):
            break
        pt = dd.get("page_token")
        if not pt:
            break
    want = len(records)
    flag = "✓ 数量一致" if real == want else f"⚠ 数量不一致 实际={real} 期望={want}"
    print(f"  {flag}")
    return ok, fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--pause", type=float, default=0.0)
    args = ap.parse_args()

    fs = FS()
    tables = fs.list_tables()
    print("现有数据表:", tables)

    DISPLAY = {
        "influencers": TBL_INFL,            # 已存在，直接用
        "search_videos": "视频数据表",
        "influencer_videos": "网红视频表",
        "search_tasks": "搜索任务表",
    }

    def tid_for(sheet):
        name = DISPLAY[sheet]
        if sheet == "influencers":
            return name
        return tables.get(name) or fs.create_table(name)

    plan = [
        ("influencers", T_INFL, INF_RECREATE_AS_TEXT, INF_TEMPLATE_LEFTOPVERS),
        ("search_videos", T_VIDS, [], []),
        ("influencer_videos", T_IVIDS, [], []),
        ("search_tasks", T_TASKS, [], []),
    ]
    tok = fail = 0
    for sheet, schema, recr, drop in plan:
        if args.sheet and sheet != args.sheet:
            continue
        tid = tid_for(sheet)
        o, f = sync(fs, sheet, tid, schema, recr, drop,
                    reset=args.reset, batch_size=args.batch, pause=args.pause)
        tok += o; fail += f
    print(f"\n========== 汇总: 成功 {tok}, 失败 {fail} ==========")


if __name__ == "__main__":
    main()
