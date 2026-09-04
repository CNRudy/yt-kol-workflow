#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 match_full_table.py 产出的 scored.json 回写飞书「网红详情表」。

写入字段：
- 匹配产品 / 品牌匹配度 / 内容契合类型 / 匹配关键词 / 开发优先级 / 推荐理由（6 个评分列，覆盖为 baby_car_camera_us 结果）
- 匹配排序组（新增 text 列："1-有邮箱+推广" / "2-其余"，便于在飞书内直接排序/分组）

用法:
    ./.venv/bin/python push_match_to_feishu.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from write_user_base import BASE_TOKEN, TABLE_IDS, run

DETAIL_TID = TABLE_IDS["网红详情表"]
HERE = os.path.dirname(os.path.abspath(__file__))
SCORED = os.path.join(HERE, "output", "us_baby_full_match", "scored.json")


def ensure_sort_field():
    """确保「匹配排序组」text 列存在（无 --yes 的 field-create）。"""
    j = run(["base", "+field-list", "--as", "user", "--base-token", BASE_TOKEN,
             "--table-id", DETAIL_TID, "--format", "json"], expect_ok=False)
    items = (j.get("data", {}).get("fields") or j.get("data", {}).get("items") or [])
    existing = {f.get("name", ""): f for f in items}
    if "匹配排序组" in existing:
        print("[字段] 匹配排序组 已存在，跳过创建")
        return
    body = {"name": "匹配排序组", "type": "text"}
    r = run(["base", "+field-create", "--as", "user", "--base-token", BASE_TOKEN,
             "--table-id", DETAIL_TID, "--json", json.dumps(body, ensure_ascii=False)],
            expect_ok=False)
    if r and r.get("ok"):
        print("[字段] 已新建「匹配排序组」(text)")
    else:
        print(f"[字段] 创建「匹配排序组」失败: {json.dumps(r, ensure_ascii=False)[:200] if r else 'no resp'}")


def upsert(rec_id, fields):
    for attempt in range(3):
        try:
            r = run(["base", "+record-upsert", "--as", "user", "--base-token", BASE_TOKEN,
                     "--table-id", DETAIL_TID, "--record-id", rec_id,
                     "--json", json.dumps(fields, ensure_ascii=False)],
                    expect_ok=False)
            if r and r.get("ok"):
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def main():
    if not os.path.exists(SCORED):
        print(f"✗ 找不到 {SCORED}，请先跑 match_full_table.py")
        return
    rows = json.load(open(SCORED, "r", encoding="utf-8"))
    print(f"[读取] scored.json: {len(rows)} 条")

    ensure_sort_field()

    updated = 0
    failed = 0
    for i, r in enumerate(rows, 1):
        fields = {
            "匹配产品": r.get("match_profile", ""),
            "品牌匹配度": r.get("fit", 0),
            "内容契合类型": r.get("match_types", ""),
            "匹配关键词": r.get("match_kw", ""),
            "开发优先级": r.get("priority", "C"),
            "推荐理由": r.get("reason", ""),
            "匹配排序组": r.get("priority_group", "2-其余"),
        }
        ok = upsert(r.get("record_id", ""), fields)
        if ok:
            updated += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"  ✗ [{i}] {r.get('cid','')} 写入失败")
        if i % 100 == 0:
            print(f"  [{i}/{len(rows)}] 已写 {updated} | 失败 {failed}")
        time.sleep(0.08)

    print(f"\n✅ 回写完成：成功 {updated} | 失败 {failed} | 总计 {len(rows)}")


if __name__ == "__main__":
    main()
