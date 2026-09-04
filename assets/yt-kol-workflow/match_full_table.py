#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对整个「网红详情表」做 baby_car_camera_us 产品匹配，按"有邮箱+推广经验"优先排序。

- 实时从飞书拉取完整网红详情表（全量，不依赖可能过期的本地缓存）
- 用当前 active 产品画像（baby_car_camera_us = WEMOH C1 婴儿车载摄像头）打分
- 排序规则：①有邮箱 AND 有亚马逊推广经验 排最前，②其余在后；组内按品牌匹配度降序
- 输出：排序后 Excel + scored.json（供回写飞书用）

用法:
    ./.venv/bin/python match_full_table.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from write_user_base import BASE_TOKEN, TABLE_IDS, run
from filter.scoring import get_active_profile, score_influencer

DETAIL_TID = TABLE_IDS["网红详情表"]
VIDEO_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_cache", "channel_videos.json")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "us_baby_full_match")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _str(v):
    if isinstance(v, list):
        return str(v[0]) if v else ""
    return str(v) if v is not None else ""


def list_all(tid, limit=200):
    """分页拉取整张表，返回 [{record_id, fields}]。"""
    out = []
    offset = 0
    while True:
        j = run([
            "base", "+record-list", "--as", "user", "--base-token", BASE_TOKEN,
            "--table-id", tid, "--limit", str(limit), "--offset", str(offset),
            "--format", "json",
        ])
        if not j or not j.get("ok"):
            break
        d = j.get("data", {})
        field_names = d.get("fields") or []
        rows = d.get("data") or []
        rids = d.get("record_id_list") or []
        for idx, row in enumerate(rows):
            if isinstance(row, list):
                flds = dict(zip(field_names, row))
            elif isinstance(row, dict):
                flds = row.get("fields", {})
            else:
                flds = {}
            rid = rids[idx] if idx < len(rids) else (
                row.get("record_id", "") if isinstance(row, dict) else "")
            out.append({"record_id": rid, "fields": flds})
        if len(rows) < limit:
            break
        offset += limit
    return out


def load_video_map():
    """从本地缓存(可能略旧)构建 Channel ID -> [video dict] 映射，用于内容契合检测。"""
    if not os.path.exists(VIDEO_CACHE):
        return {}
    with open(VIDEO_CACHE, "r", encoding="utf-8") as f:
        data = json.load(f)
    vmap = {}
    for rec in data.get("records", []):
        f = rec.get("fields", {})
        cid = _str(f.get("Channel ID", ""))
        if not cid:
            continue
        vmap.setdefault(cid, []).append({
            "title": _str(f.get("Video Title", "")),
            "tags": _str(f.get("Tags", "")),
            "description": _str(f.get("字幕内容", "")),
            "view_count": _num(f.get("Views")),
            "engagement_rate": _num(f.get("互动率(%)")),
        })
    return vmap


def main():
    profile = get_active_profile()
    if not profile:
        print("⚠ 未配置 active 产品画像")
        return
    print(f"[画像] {profile.get('name')} | 市场={profile.get('markets')} | "
          f"min_views={profile.get('min_views')} min_eng={profile.get('min_engagement')}")

    print("[拉取] 网红详情表(实时全量)…")
    details = list_all(DETAIL_TID)
    print(f"  👤 网红记录 {len(details)} 个")

    print("[加载] 视频缓存(本地)…")
    vmap = load_video_map()
    print(f"  📹 覆盖频道 {len(vmap)} 个")

    rows = []
    for rec in details:
        f = rec.get("fields", {})
        cid = _str(f.get("Channel ID", ""))
        email_raw = _str(f.get("联系邮箱", "")) or _str(f.get("候选邮箱", ""))
        email_status = _str(f.get("邮箱状态", ""))
        promo = _str(f.get("亚马逊推广经验", ""))

        has_email = (email_status == "已获取") or bool(email_raw.strip())
        has_promo = promo not in ("", "未发现", "未发现推广经验")
        priority_group = "1-有邮箱+推广" if (has_email and has_promo) else "2-其余"

        detail = {
            "amazon_promo_level": promo,
            "email_status": email_status,
            "rep_video_engagement": _num(f.get("代表视频互动率")),
            "country": _str(f.get("国家/地区", "")),
            "activity_status": _str(f.get("断更评估", "")),
            "channel_description": _str(f.get("频道描述", "")),
            "rep_video_title": _str(f.get("代表视频标题", "")),
        }
        videos = vmap.get(cid, [])
        scored = score_influencer(detail, videos, profile)

        rows.append({
            "record_id": rec.get("record_id", ""),
            "cid": cid,
            "channel_name": _str(f.get("Channel Name", "")),
            "kol_name": _str(f.get("KOL Name", "")),
            "country": detail["country"],
            "subs": _str(f.get("订阅数", "")),
            "channel_url": _str(f.get("频道URL", "")),
            "email_status": email_status,
            "contact_email": email_raw,
            "promo": promo,
            "fit": scored["brand_fit_score"],
            "priority": scored["dev_priority"],
            "priority_score": scored["priority_score"],
            "match_types": scored["content_types"],
            "match_kw": scored["matched_keywords"],
            "reason": scored["recommend_reason"],
            "has_email": has_email,
            "has_promo": has_promo,
            "priority_group": priority_group,
            "match_profile": scored["match_profile"],
        })

    # 排序：①排序组升序(1在前) ②品牌匹配度降序 ③优先分降序
    rows.sort(key=lambda r: (r["priority_group"], -r["fit"], -r["priority_score"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # 统计
    grp1 = [r for r in rows if r["priority_group"].startswith("1")]
    print(f"\n总记录: {len(rows)} | 有邮箱+推广: {len(grp1)} | 其余: {len(rows)-len(grp1)}")
    if grp1:
        avg1 = round(sum(r["fit"] for r in grp1) / len(grp1), 1)
        print(f"  ①组平均品牌匹配度: {avg1} | S/A/B/C="
              + "/".join(f"{t}={sum(1 for r in grp1 if r['priority']==t)}" for t in ('S','A','B','C')))
    rest = [r for r in rows if not r["priority_group"].startswith("1")]
    if rest:
        avg2 = round(sum(r["fit"] for r in rest) / len(rest), 1)
        print(f"  ②组平均品牌匹配度: {avg2} | S/A/B/C="
              + "/".join(f"{t}={sum(1 for r in rest if r['priority']==t)}" for t in ('S','A','B','C')))

    # 输出 Excel
    os.makedirs(OUT_DIR, exist_ok=True)
    xlsx_path = os.path.join(OUT_DIR, "全表匹配_美国婴儿车载摄像头.xlsx")
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "全表匹配排序"
        headers = ["排名", "排序组", "Channel Name", "KOL Name", "国家/地区", "订阅数",
                   "品牌匹配度", "开发优先级", "匹配关键词", "内容契合类型",
                   "亚马逊推广经验", "邮箱状态", "联系邮箱", "推荐理由", "频道URL", "Channel ID"]
        ws.append(headers)
        for r in rows:
            ws.append([
                r["rank"], r["priority_group"], r["channel_name"], r["kol_name"],
                r["country"], r["subs"], r["fit"], r["priority"], r["match_kw"],
                r["match_types"], r["promo"], r["email_status"], r["contact_email"],
                r["reason"], r["channel_url"], r["cid"],
            ])
        wb.save(xlsx_path)
        print(f"\n✅ Excel: {xlsx_path}")
    except Exception as e:
        print(f"  ! Excel 写入失败: {e}")

    # 输出 scored.json 供回写飞书
    json_path = os.path.join(OUT_DIR, "scored.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"✅ scored.json: {json_path} ({len(rows)} 条)")

    # Top 20 预览
    print("\n=== Top 20（有邮箱+推广优先，再按匹配度）===")
    for r in rows[:20]:
        print(f"  #{r['rank']:>4} {r['priority_group']} | {r['fit']:>3} {r['priority']} | "
              f"{r['channel_name'][:28]:<28} | {r['country']:<4} | {r['promo']:<10} | 邮箱:{r['email_status']}")


if __name__ == "__main__":
    main()
