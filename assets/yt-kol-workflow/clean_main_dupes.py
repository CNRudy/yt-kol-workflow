#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理主表（网红详情表）中重复 Channel ID 的记录。

背景：主表 2118 行里只有 1821 个唯一 Channel ID，297 个频道被重复导入，
这是派生「红人表」出现重复行的根因（红人表只是镜像主表）。

安全设计：
  * 删除前先把主表全量备份到 output/backup/（含 record_id，可用于还原）
  * 每个重复组保留「信息最全」的一条（非空字段多、且有匹配产品的优先）
  * 支持 --dry-run 只看明细不删除

用法:
    python clean_main_dupes.py --dry-run   # 只看明细
    python clean_main_dupes.py             # 备份 + 删除
"""
import json
import os
import sys
import time
import types
from collections import Counter
from datetime import datetime

try:
    import dotenv  # noqa: F401
except ImportError:
    _m = types.ModuleType("dotenv")
    _m.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _m

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import write_user_base as wb

wb.LARK = "/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["LARK_CLI_NO_PROXY_WARN"] = "1"

from write_user_base import BASE_TOKEN, TABLE_IDS  # noqa: E402
from score_influencers import list_all  # noqa: E402

SRC_TID = TABLE_IDS["网红详情表"]
BATCH = 200
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "backup")


def norm(v):
    if isinstance(v, list):
        v = v[0] if v else ""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{float(v):.6g}"
    return str(v).strip()


def richness(rec):
    """信息完整度：非空字段数 + 有匹配产品/邮箱额外加权。"""
    f = rec["fields"]
    n = sum(1 for v in f.values() if norm(v))
    if norm(f.get("匹配产品")):
        n += 100
    if norm(f.get("联系邮箱")):
        n += 50
    if norm(f.get("备注")):
        n += 50
    return n


def main():
    dry = "--dry-run" in sys.argv

    print(f"[读取] 主表 网红详情表 ({SRC_TID}) …")
    rows = list_all(SRC_TID)
    print(f"  共 {len(rows)} 行")

    # 备份
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"网红详情表_备份_{ts}.json")
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump({"table_id": SRC_TID, "exported_at": ts, "records": rows},
                  fh, ensure_ascii=False, indent=1)
    print(f"[备份] 已保存全量快照 → {backup_path}")

    # 按 Channel ID 分组
    groups = {}
    for r in rows:
        cid = norm(r["fields"].get("Channel ID"))
        if cid:
            groups.setdefault(cid, []).append(r)

    dup_groups = {c: rs for c, rs in groups.items() if len(rs) > 1}
    to_delete = []
    for cid, rs in dup_groups.items():
        rs_sorted = sorted(rs, key=richness, reverse=True)
        to_delete.extend(rs_sorted[1:])   # 保留信息最全的一条

    del_ids = [r["record_id"] for r in to_delete]
    print("\n" + "=" * 62)
    print("重复清理计划")
    print("=" * 62)
    print(f"  总行数        : {len(rows)}")
    print(f"  唯一 ChannelID: {len(groups)}")
    print(f"  重复组        : {len(dup_groups)}")
    print(f"  将删除        : {len(del_ids)} 行（每组保留信息最全的 1 条）")
    print(f"  清理后预计    : {len(rows) - len(del_ids)} 行")

    # 重复来源关键词分布
    kw = Counter()
    for r in to_delete:
        kw[norm(r["fields"].get("来源关键词")) or "(空)"] += 1
    print("\n  待删除行的来源关键词分布（前10）:")
    for k, n in kw.most_common(10):
        print(f"    {n:>4}  {k}")

    # 样例：展示重复组内两条的差异
    print("\n  重复组样例（保留 vs 删除）:")
    for cid, rs in list(dup_groups.items())[:3]:
        rs_sorted = sorted(rs, key=richness, reverse=True)
        keep, drop = rs_sorted[0], rs_sorted[1]
        print(f"\n   Channel ID {cid}")
        for tag, r in (("保留", keep), ("删除", drop)):
            f = r["fields"]
            print(f"     [{tag}] rid={r['record_id']} 完整度={richness(r)} "
                  f"匹配产品={str(norm(f.get('匹配产品')))[:28]!r} "
                  f"邮箱={'有' if norm(f.get('联系邮箱')) else '无'} "
                  f"备注={'有' if norm(f.get('备注')) else '无'}")

    if dry:
        print(f"\n[dry-run] 未删除任何数据。备份已保存: {backup_path}")
        return

    print(f"\n[删除] 分 {(len(del_ids)+BATCH-1)//BATCH} 批删除 {len(del_ids)} 行…")
    deleted = 0
    for i in range(0, len(del_ids), BATCH):
        chunk = del_ids[i:i + BATCH]
        r = wb.run(["base", "+record-delete", "--as", "user", "--base-token", BASE_TOKEN,
                    "--table-id", SRC_TID, "--yes",
                    "--json", json.dumps({"record_id_list": chunk}, ensure_ascii=False)],
                   expect_ok=False)
        if r and r.get("ok"):
            deleted += len(chunk)
            print(f"    -{len(chunk)} 行")
        else:
            print(f"    ❌ 删除批次失败: {json.dumps(r, ensure_ascii=False)[:300]}")
        time.sleep(0.2)

    final = list_all(SRC_TID)
    fc = Counter(norm(x["fields"].get("Channel ID")) for x in final)
    print(f"\n✅ 完成: 删除 {deleted} 行")
    print(f"   主表现有 {len(final)} 行 / 唯一 Channel ID {len(fc)} / 剩余重复 {sum(1 for n in fc.values() if n > 1)}")
    print(f"   备份文件（如需还原）: {backup_path}")


if __name__ == "__main__":
    main()
