#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restore promo/email fields from local cache after write_user_base.py clears the table.
Only restores channel-level data (promo/email) — NOT score data (scores are product-specific
and need recalculation with the new product profile).

Usage:
    ./.venv/bin/python restore_cached_fields.py
"""
import os
import json, subprocess, os, sys, time

BASE_DIR = "/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow"
LARK = "/Users/coscod/.workbuddy/binaries/node/versions/22.22.2/bin/lark-cli"
BASE_TOKEN = os.environ["FEISHU_BASE_TOKEN"]  # 从 .env / 环境变量读取，勿提交真实值
TABLE_ID = "tbl4rnFUM9jJXvCQ"  # 网红详情表

# Only restore channel-level promo/email fields (NOT score fields — those are product-specific)
PROMO_FIELDS = [
    "邮箱", "邮箱来源", "邮箱出现视频数", "候选邮箱",
    "亚马逊推广经验", "Amazon带货视频数", "推广视频数",
    "Amazon Storefront", "推广证据",
]


def _str(v):
    """Normalize select field values (returned as list by Feishu)."""
    if isinstance(v, list):
        return v[0] if v else ""
    if isinstance(v, (int, float)):
        return v
    return str(v) if v else ""


def load_cache():
    cache_path = os.path.join(BASE_DIR, "local_cache", "influencers.json")
    if not os.path.exists(cache_path):
        print(f"[ERROR] 本地缓存不存在: {cache_path}")
        sys.exit(1)
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_upsert(fields_data, channel_id):
    """Upsert one record by Channel ID."""
    # Build the JSON payload
    json_payload = {
        "records": [{"fields": fields_data}],
        "field_norm": True,
    }
    # Write to temp file
    tmp_path = os.path.join(BASE_DIR, "_restore_tmp.json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False)

    env = os.environ.copy()
    env["LARK_CLI_NO_PROXY_WARN"] = "1"

    cmd = [
        LARK, "--as", "user",
        "+bitable-record-upsert",
        "--app-token", BASE_TOKEN,
        "--table-id", TABLE_ID,
        "--unique-key", "Channel ID",
        "--json", "@_restore_tmp.json",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, env=env,
            cwd=BASE_DIR,
        )
        ok = result.returncode == 0
        if not ok:
            err = result.stderr.strip()[:200] if result.stderr else result.stdout.strip()[:200]
            return False, err
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def main():
    influencers = load_cache()
    print(f"[缓存] 本地缓存: {len(influencers)} 条红人")

    restored = 0
    skipped = 0
    failed = 0

    for i, inf in enumerate(influencers):
        channel_id = inf.get("Channel ID", "")
        if not channel_id:
            skipped += 1
            continue

        # Build fields dict from cache
        fields = {}
        for field in PROMO_FIELDS:
            if field in inf:
                val = _str(inf[field])
                if val:
                    fields[field] = val

        if not fields:
            skipped += 1
            continue

        ok, err = run_upsert(fields, channel_id)
        if ok:
            restored += 1
        else:
            failed += 1
            if failed <= 3:
                print(f"  [FAIL] {channel_id}: {err}")

        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(influencers)} (恢复={restored}, 跳过={skipped}, 失败={failed})", flush=True)

    print(f"\n[完成] 恢复={restored}, 跳过={skipped}, 失败={failed}, 总计={len(influencers)}")

    # Clean up temp file
    tmp_path = os.path.join(BASE_DIR, "_restore_tmp.json")
    try:
        os.remove(tmp_path)
    except Exception:
        pass


if __name__ == "__main__":
    main()
