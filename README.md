# YouTube KOL Workflow → Feishu/Lark Bitable

> Search YouTube influencers by product keywords, filter and score them, sync to Feishu/Lark Bitable for team collaboration.

[中文说明](#中文说明) | [English](#overview)

> 🤖 **New to coding? Install & run everything with an AI assistant:**
> - [Install with AI — English Guide](INSTALL_WITH_AI_EN.md)
> - [用 AI 安装使用 — 中文教程](INSTALL_WITH_AI_CN.md)

## ⚙️ Configuration after clone

```bash
cp assets/yt-kol-workflow/.env.example assets/yt-kol-workflow/.env
# then edit .env:
#   YOUTUBE_API_KEY      = your YouTube Data API v3 key (required)
#   FEISHU_AUTH_MODE     = auto (default) | cli | app
#   FEISHU_BASE_TOKEN    = your Feishu Base token (main KOL Base)
#   FEISHU_BASE_TOKEN_CFC1 = optional second Base (product line B)
#   FEISHU_APP_ID / FEISHU_APP_SECRET = only needed in "app" auth mode
```

> 🔒 **No real credentials are stored in this repository.** All Feishu Base
> tokens and app secrets are read from environment variables / `.env` at
> runtime (scripts fall back to `os.environ.get("FEISHU_BASE_TOKEN", "")`).
> Never commit your real `.env`, `config.json`, `local_cache/`, `output/`, or
> any downloaded batch data (`.gitignore` already blocks these).

## Overview


This workflow helps you discover YouTube influencers (KOLs) relevant to your product, automatically detect their Amazon promotion experience and contact emails, score them by product fit, and sync everything into a Feishu/Lark Bitable for your team to filter, sort, and reach out.

### Key Features

- **Batch YouTube Search**: Search multiple keywords at once, filter by views/subscribers/engagement
- **Channel Deduplication**: Cross-batch deduplication by Channel ID
- **Amazon Promo Detection**: Automatically classify influencers' Amazon promotion experience:
  - `Amazon Storefront` (highest value - Amazon Influencer Program member)
  - `Amazon Affiliate` (Associate with `?tag=` links)
  - `Amazon Links` (has amzn.to/a.co/amazon links)
  - `Other Affiliate` (geni.us/LTK/ShopMy)
  - `Sponsored` (#ad/paid promotion)
  - `Not Found`
- **Email Extraction**: Multi-source email extraction (channel description + video descriptions), ranked by cross-video frequency
- **Product-Fit Scoring**: Score influencers S/A/B/C based on content relevance, promo experience, engagement, and activity
- **Feishu/Lark Sync**: One-command sync to your own Feishu Base (you own all data, fields, and views)
- **Local Cache**: JSON cache for fast offline analysis (2700x faster than API pagination)

### Architecture

```
YouTube Search (main.py batch)
   └─> output/<timestamp>_batch/  local Excel (per-keyword files)
         └─> merge-output          merge & dedup → kol_summary_tables.xlsx (4 sheets)
               └─> Feishu Sync      clear + rewrite 4 tables → your editable Base
                     └─> Enrich      refresh_promo_lark.py (promo+email) + score_influencers.py (scoring)
                           └─> Derive   sync_hongren_table.py (incremental summary, no table reset) + export_local_cache.py (cache)
```

## Quick Start

### Prerequisites

- Python 3.9+
- [lark-cli](https://github.com/larksuite/lark-cli) (for Feishu sync, optional)
- YouTube Data API v3 key

### Installation

```bash
git clone https://github.com/yourusername/yt-kol-workflow.git
cd yt-kol-workflow/assets/yt-kol-workflow

# Create venv and install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: fill in YOUTUBE_API_KEY
```

### Usage

```bash
# 1. Create a keywords file (one keyword per line, optionally with count: keyword,100)
echo "baby car camera\nbaby monitor car\nrear facing car seat" > keywords.txt

# 2. Run batch search
python main.py batch --keywords-file keywords.txt -o output/my_batch --region US --lang en

# 3. Merge batches (dedup by Channel ID)
python main.py merge-output output/my_batch -o output/summary/kol_summary_tables.xlsx

# 4. Sync to Feishu (first time: creates Base + tables)
python sync_to_user_base.py
# Subsequent syncs (clear + rewrite):
python write_user_base.py

# 5. Enrich: detect Amazon promo experience + extract emails
python refresh_promo_lark.py

# 6. Score: product-fit scoring (S/A/B/C)
python score_influencers.py

# 7. Incremental-sync summary table + export local cache (since 2026-09, replaces build_hongren_table.py)
python sync_hongren_table.py --dedupe
python export_local_cache.py
```

### Product Profile Configuration

Edit `product_profiles.json` to define your product:

```json
{
  "active": "my_product",
  "profiles": {
    "my_product": {
      "name": "My Product",
      "keywords": ["keyword1", "keyword2"],
      "markets": ["US"],
      "min_views": 10000,
      "min_engagement": 2.0
    }
  }
}
```

## Project Structure

```
yt-kol-workflow/
├── assets/yt-kol-workflow/
│   ├── main.py                  # Search / merge / sync entry point
│   ├── write_user_base.py       # Feishu sync (clear + rewrite)
│   ├── sync_to_user_base.py     # First-time Base creation
│   ├── refresh_promo_lark.py    # Promo detection + email extraction
│   ├── score_influencers.py     # Product-fit scoring (S/A/B/C)
│   ├── sync_hongren_table.py    # Incremental summary sync (preserves manual columns, --dedupe)
│   ├── export_local_cache.py    # Export to local JSON cache
│   ├── local_cache_reader.py    # Fast local cache reader
│   ├── product_profiles.json    # Product profile config
│   ├── config.py                # Configuration
│   ├── youtube/                 # YouTube API client modules
│   ├── feishu/                  # Feishu/Lark API modules
│   ├── filter/                  # Filtering, scoring, email, promo detection
│   ├── workflow/                # Workflow phases (search, filter, enrich)
│   ├── export/                  # Excel export modules
│   ├── tests/                   # Test suite
│   └── requirements.txt
├── SKILL.md                     # Skill definition
├── 使用说明与注意事项.md          # User guide (Chinese)
└── README.md
```

## Scoring System

| Level | Meaning |
|-------|---------|
| **S** | Perfect match + Amazon Storefront/Affiliate + has email + active |
| **A** | Good match + Amazon promo experience + has email |
| **B** | Some match or has promo/email but not both |
| **C** | Low relevance, no promo experience, no email |

## Important Notes

- `write_user_base.py` **clears and rewrites** all records. Manual field edits in Feishu are preserved, but per-record values will be overwritten on sync.
- The promo detection and email extraction scripts require YouTube API access (consume quota: ~2 units per channel).
- For large datasets (>20K rows in influencer_videos), the Feishu table has a record limit. Use local cache for analysis.
- Set `HTTPS_PROXY` environment variable if YouTube API is blocked in your region.

## License

See [LICENSE](assets/yt-kol-workflow/LICENSE).

---

## 中文说明

YouTube 网红搜索工作流：用关键词在 YouTube 搜索网红 → 过滤筛选 → 检测亚马逊推广经验和邮箱 → 按产品匹配度评分 → 同步到飞书多维表格。

### 核心功能

- 批量关键词搜索，按播放量/订阅数/互动率过滤
- 跨批次按 Channel ID 去重
- 自动检测亚马逊推广经验（6 级分类）
- 多源邮箱抽取（频道简介 + 视频描述，按频次排序）
- 产品匹配度评分（S/A/B/C 优先级）
- 一键同步飞书多维表格
- 本地 JSON 缓存（秒级读取，比 API 快 2700 倍）

### 快速开始

```bash
# 1. 克隆并安装
git clone https://github.com/yourusername/yt-kol-workflow.git
cd yt-kol-workflow/assets/yt-kol-workflow
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env 填入 YOUTUBE_API_KEY

# 3. 搜索 → 合并 → 同步 → 补算 → 评分
python main.py batch --keywords-file keywords.txt -o output/my_batch
python main.py merge-output output/my_batch -o output/summary/kol_summary_tables.xlsx
python sync_to_user_base.py        # 首次建表
python refresh_promo_lark.py       # 补算 promo + 邮箱
python score_influencers.py        # 评分写回
python sync_hongren_table.py --dedupe  # 增量同步红人表（9/3 起取代 build_hongren_table.py 删表重建）
python export_local_cache.py       # 导出本地缓存
```

详细使用说明见 [使用说明与注意事项.md](使用说明与注意事项.md)。
