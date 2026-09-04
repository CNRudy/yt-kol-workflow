# Install & Use This Workflow with an AI Assistant (English Guide)

> This guide shows you how to install and run the YouTube KOL Workflow entirely through an AI coding assistant (WorkBuddy, Codex CLI, Cursor, Windsurf, etc.).
>
> No need to memorize commands or know Python — just paste prompts into your AI's chat box.

---

## Table of Contents

1. [Compatible AI Platforms](#1-compatible-ai-platforms)
2. [Prerequisites](#2-prerequisites)
3. [Installation (Paste Prompts to AI)](#3-installation-paste-prompts-to-ai)
4. [Configure YouTube API Key](#4-configure-youtube-api-key)
5. [Prepare Keywords & Start Searching](#5-prepare-keywords--start-searching)
6. [Merge Search Results](#6-merge-search-results)
7. [Sync to Feishu / Lark Bitable](#7-sync-to-feishu--lark-bitable)
8. [Detect Amazon Promo Experience + Emails](#8-detect-amazon-promo-experience--emails)
9. [Product-Fit Scoring](#9-product-fit-scoring)
10. [Build Summary Table + Local Cache](#10-build-summary-table--local-cache)
11. [AI Prompt Cheat Sheet](#11-ai-prompt-cheat-sheet)
12. [FAQ](#12-faq)

---

## 1. Compatible AI Platforms

Any AI assistant that can "read/write local files + execute terminal commands" will work:

| Platform | Support | Notes |
|----------|---------|-------|
| **WorkBuddy** | Full | Auto-loads SKILL.md, AI understands the entire workflow |
| **Codex CLI (OpenAI)** | Full | Reads SKILL.md and executes all commands |
| **Cursor** | Full | Paste prompts in Composer/Chat |
| **Windsurf** | Full | Paste prompts in Cascade mode |
| **GitHub Copilot Chat** | Partial | AI generates commands; you run them manually in terminal |
| **Other file-capable AI** | Should work | As long as it can read/write files and run commands |

> **Recommended: WorkBuddy** — This project ships with a `SKILL.md` that WorkBuddy auto-loads, so the AI understands all workflow details without manual prompting.

---

## 2. Prerequisites

Before starting, make sure your machine has:

### Required

- **Python 3.9+**: Run `python3 --version` to verify
- **YouTube Data API v3 Key**: Get one free from [Google Cloud Console](https://console.cloud.google.com/)
  - Enable "YouTube Data API v3"
  - Create an API Key (free quota: 10,000 units/day)

### Optional (only for Feishu/Lark sync)

- **Node.js + npx**: Required by lark-cli
- **Feishu/Lark account**: For browser OAuth authorization
- **Network proxy**: If YouTube API is blocked in your region, configure an HTTP proxy

### Not Required

- No Python knowledge needed
- No manual dependency installation (AI does it)
- No command-line memorization (AI builds commands for you)

---

## 3. Installation (Paste Prompts to AI)

### Option A: Clone from GitHub

Paste this prompt into your AI assistant:

```
Please help me clone the YouTube KOL Workflow project and initialize it:

1. Clone the repo: git clone https://github.com/yourusername/yt-kol-workflow.git
2. Enter the project directory: cd yt-kol-workflow/assets/yt-kol-workflow
3. Create a Python virtual environment: python3 -m venv .venv
4. Activate it: source .venv/bin/activate
5. Install dependencies: pip install -r requirements.txt
6. Create config files from examples:
   - cp .env.example .env
   - cp keywords.example.txt keyword.txt
   - cp brand_exclusions.example.json brand_exclusions.json
7. Tell me what to do next after installation is complete.
```

> **Windows users**: Step 4 becomes `.venv\Scripts\activate`

The AI will execute all steps automatically and report the result.

### Option B: Use the bundled bootstrap script

If your AI is in the project root:

```
Please run the project's bootstrap script:
python scripts/bootstrap_workflow.py --target ./yt-kol-workflow --install-deps

After completion, tell me the result and next steps.
```

### Option C: Already have the project files

If you already placed the project in a directory:

```
I've placed the yt-kol-workflow project at /path/to/yt-kol-workflow/assets/yt-kol-workflow.
Please help me:
1. Create a .venv virtual environment there and install requirements.txt
2. Copy .env.example to .env
3. Copy keywords.example.txt to keyword.txt
```

---

## 4. Configure YouTube API Key

After installation, configure your API key. Paste this to your AI:

```
Please edit the .env file and set YOUTUBE_API_KEY to: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

(Replace the above with your real API key)

Also check if these optional settings need to be configured:
- HTTPS_PROXY (if you need a proxy to reach YouTube API)
- FEISHU_AUTH_MODE (Feishu auth mode, default "auto" is fine)
```

### How to Get a YouTube API Key

If you're unsure how to get one, just ask your AI:

```
I don't know how to get a YouTube Data API v3 key. Please walk me through the steps.
```

The AI will give you a complete walkthrough.

### Configure a Proxy (If Needed)

If YouTube API is blocked in your region:

```
Please set the following in .env:
- HTTPS_PROXY=http://127.0.0.1:7890
- HTTP_PROXY=http://127.0.0.1:7890

(Replace the port with your actual proxy port)
```

---

## 5. Prepare Keywords & Start Searching

### Create a Keywords File

Paste this prompt to your AI to create a keywords file and start searching:

```
Please create a keyword.txt file in the project directory with one keyword per line:

baby monitor
baby car camera
rear facing car seat
newborn essentials
parenting products

After saving, run the batch search:
source .venv/bin/activate
python main.py batch --keywords-file keyword.txt -o output/my_first_batch --sort-order relevance --yes --no-feishu
```

> - `--no-feishu`: Generate local Excel only, skip Feishu sync (recommended for first run)
> - `--sort-order relevance`: Sort by relevance for higher quality
> - `--yes`: Skip interactive confirmation
> - `-o output/my_first_batch`: Specify output directory

### How Long Does It Take?

- Each keyword costs ~100 API quota units (search.list)
- 10 keywords ≈ 5–10 minutes
- 17 keywords ≈ 15–30 minutes
- If the AI runs it as a background task, you can do other things — you'll be notified when done

### After Search Completes

The AI will show you the output files:

```
output/my_first_batch/
├── search_tasks_all.xlsx       # Search task summary
├── search_videos_all.xlsx      # Video data
├── influencers_all.xlsx        # Influencer details
└── influencer_videos_all.xlsx  # Influencer-video mappings
```

---

## 6. Merge Search Results

If you ran multiple search rounds (e.g., English keywords first, then German), merge them:

```
Please merge multiple search batches into one summary table:

python main.py merge-output output/first_batch output/second_batch -o output/summary/kol_summary_tables.xlsx

Deduplication is by Channel ID — the same influencer won't appear twice.
```

> **Important**: Batch directories are positional arguments (just list them after the command), not `--batch-dirs`.

For a single batch:

```
Please merge this batch:
python main.py merge-output output/my_first_batch -o output/summary/kol_summary_tables.xlsx
```

---

## 7. Sync to Feishu / Lark Bitable

### First-Time Setup (Create Feishu Base)

```
Please run Feishu initialization:
python main.py feishu-setup

This command will:
1. Detect or install lark-cli
2. Open browser for Feishu OAuth authorization
3. Create a new Bitable (Base)
4. Create 4 standard data tables

Do I need to do anything in the browser?
```

### First Data Sync

After the Base is created:

```
Please run the first data sync:
python sync_to_user_base.py

This creates the Base + 4 tables and writes all data. Run this only once.
```

### Subsequent Syncs (Clear + Rewrite)

After each new search and merge:

```
Please sync updated data to Feishu:
python write_user_base.py

Note: This clears all 4 tables and rewrites. Field configurations and views are preserved,
but per-record manual values will be overwritten.
```

> **Important notes**:
> - `write_user_base.py` uses "clear + rewrite" mode — manual per-record annotations (like "contacted") will be lost on next sync
> - Field configurations (add fields, change types) and views (filters, groupings) are always preserved
> - To preserve manual annotations, switch to upsert mode (advanced — ask your AI)

---

## 8. Detect Amazon Promo Experience + Emails

After search is complete, automatically detect each influencer's Amazon promotion experience and contact emails:

```
Please run the promo detection and email extraction:
source .venv/bin/activate
python refresh_promo_lark.py

This script will:
1. Fetch the latest 25 video descriptions per channel (via YouTube API)
2. Auto-classify Amazon promo experience (6 tiers)
3. Multi-source email extraction (ranked by cross-video frequency)
4. Write results back to the Feishu influencer details table
5. Existing emails are NOT overwritten
6. Supports resume — re-running only processes unprocessed channels

Estimated time: ~30 minutes for 500 channels. Recommended to run in background.
```

### Promo Experience Tiers

| Tier | Meaning | Value |
|------|---------|-------|
| Amazon Storefront | Amazon Influencer Program member | Highest |
| Amazon Affiliate | Associate with ?tag= affiliate links | High |
| Amazon Links | Has amzn.to/a.co/amazon links | Medium |
| Other Affiliate | geni.us/LTK/ShopMy etc. | Medium |
| Sponsored | #ad/paid promotion | Medium |
| Not Found | No promo signals detected | Low |

---

## 9. Product-Fit Scoring

Score each influencer with S/A/B/C priority based on your product profile:

### Step 1: Configure Product Profile

```
Please edit product_profiles.json and add a new product profile:

{
  "active": "my_product_name",
  "profiles": {
    "my_product_name": {
      "name": "My Product Name",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "content_types": ["review", "unboxing", "tutorial"],
      "markets": ["US"],
      "min_views": 10000,
      "min_engagement": 2.0
    }
  }
}

Make sure "active" points to the new profile name.
```

### Step 2: Run Scoring

```
Please run product-fit scoring:
python score_influencers.py

Scoring logic:
- Video titles/Tags/descriptions matched against product keywords → content fit 0-100
- Amazon promo experience + email + engagement + update frequency → S/A/B/C priority
- Results written to 6 Feishu columns
- Does NOT consume YouTube API quota (reads Feishu data only)
- Supports resume

Preview first with --dry-run:
python score_influencers.py --dry-run
```

### Scoring Tiers

| Tier | Meaning |
|------|---------|
| **S** | Perfect match + Amazon Storefront/Affiliate + has email + active |
| **A** | Good match + Amazon promo experience + has email |
| **B** | Partial match, or has promo/email but not both |
| **C** | Low relevance, no promo experience, no email |

---

## 10. Build Summary Table + Local Cache

### Build Summary Red-Influencer Table

```
Please run the summary table builder:
python build_hongren_table.py

This derives a 25-column summary table from the influencer details table, including promo/email/scoring columns.
Each rebuild deletes and recreates the table (table_id changes). The script handles this automatically.
```

### Export Local Cache

```
Please export the local cache:
python export_local_cache.py

This exports all 4 Feishu tables as local JSON files for instant offline analysis.
Cache directory: local_cache/
  - influencers.json    (influencer details)
  - videos.json         (video data)
  - channel_videos.json (influencer-video mappings)
  - search_tasks.json   (search tasks)
  - hongren.json        (summary table)

Always run this after writing to Feishu, otherwise scripts will read stale data.
```

---

## 11. AI Prompt Cheat Sheet

Copy-paste these prompts directly to your AI assistant:

### One-Shot Full Pipeline

```
Please search YouTube influencers with these keywords, then merge, sync to Feishu,
detect promo + emails, score, build summary table, and export local cache:
keyword1, keyword2, keyword3

Product: XXX (brief description)
Target market: US
Search region: US
Language: en
```

### Step-by-Step Quick Reference

| What You Want | Prompt to Paste |
|---------------|-----------------|
| Install project | `Clone yt-kol-workflow, set up venv, install deps, create config files` |
| Set API Key | `Set YOUTUBE_API_KEY=your_key in .env` |
| Search influencers | `Run batch search with keyword.txt, output to output/new_batch` |
| Merge batches | `Merge output/batchA and output/batchB into output/summary/kol_summary_tables.xlsx` |
| Create Feishu Base | `Run sync_to_user_base.py to create Feishu Base and 4 tables` |
| Sync to Feishu | `Run write_user_base.py to sync data to Feishu` |
| Detect promo+email | `Run refresh_promo_lark.py to detect Amazon promo experience and extract emails` |
| Score | `Run score_influencers.py to assign S/A/B/C scores` |
| Build summary table | `Run build_hongren_table.py to build the summary influencer table` |
| Export cache | `Run export_local_cache.py to export local JSON cache` |
| Preview only | `Add --dry-run to score_influencers.py to preview before writing` |
| Set proxy | `Set HTTPS_PROXY=http://127.0.0.1:7890 in .env` |

### Advanced Options

| Scenario | Prompt |
|----------|--------|
| Search without Feishu | `Add --no-feishu to only generate local Excel` |
| Change region/language | `Add --region DE --lang de for Germany/German` |
| Adjust filter thresholds | `Add --min-views 5000 --min-engagement 2 --filter-mode and` |
| Only medium-length videos | `Add --video-duration medium` |
| Only videos from 2025+ | `Add --published-after 2025-01-01` |
| Max 50 results per keyword | `Add --max-results 50` |
| Sort by view count | `Add --sort-order viewCount` |
| Backfill existing influencers | `Run refresh_promo_lark.py — existing emails are preserved, supports resume` |

---

## 12. FAQ

### Q: AI says "YouTube API Key not found"

Tell the AI:
```
Please check .env for YOUTUBE_API_KEY — the value should start with "AIza".
If the file doesn't exist, copy .env.example to .env first, then edit.
```

### Q: Feishu sync says "permission denied"

```
Feishu sync reports a permission error. Please re-authorize:
lark-cli --profile kol-workflow auth login --scope 'bitable:app:readonly bitable:app base:record:retrieve'
Then retry the sync.
```

### Q: Search results are empty or very few

```
Please help me check:
1. Are keywords too narrow or too broad?
2. Try --min-views 5000 --min-engagement 2 (lower thresholds)
3. Try --filter-mode or (default — either threshold passing is enough)
4. Switch to --sort-order viewCount (may surface more results)
5. Confirm --region and --lang match (e.g., --region DE --lang de for German market)
```

### Q: YouTube API quota exhausted

```
YouTube free quota is 10,000 units/day. Each keyword search costs 100 units.
If exhausted today, it resets at midnight Pacific Time.
You can request a quota increase in Google Cloud Console.
```

### Q: Network timeout / API unreachable

```
Please check if YouTube API is reachable:
curl -s "https://www.googleapis.com/youtube/v3/videos?part=snippet&id=test&key=YOUR_KEY" | head

If it times out, set proxy in .env:
HTTPS_PROXY=http://127.0.0.1:7890
```

### Q: What's my proxy port?

```
Please detect available proxy ports on my system:
- Check Clash: lsof -i :7890
- Check V2Ray: lsof -i :10808
- Check env vars: echo $HTTPS_PROXY
```

### Q: Can't see .env file on macOS

`.env` is a hidden file. Press `Command + Shift + .` in Finder to show hidden files.
Or just ask the AI:
```
Please read the .env file and modify YOUTUBE_API_KEY
```

### Q: write_user_base.py overwrote my manual annotations

This is expected behavior. `write_user_base.py` uses "clear + rewrite" mode.
```
Please help me understand:
- Field configurations and views are always preserved
- Per-record manual values (like "contacted" status) are overwritten
- To preserve manual annotations, switch to upsert mode
- Workaround: Create a separate "manual tracking" table in Feishu, linked by Channel ID
```

### Q: Second search round — will first round data be lost?

```
It depends on which directories you pass to merge-output:
- Only pass the second round → first round disappears from Feishu
- Pass both old + new directories → all preserved, deduplicated by Channel ID
- Correct approach: Search each keyword only once; accumulate across rounds via merge-output
```

### Q: Influencer-videos table is too large to sync

Feishu has a per-table record limit (~20,000–50,000 rows depending on config).
```
If the influencer-videos table exceeds the limit:
1. Don't sync that table to Feishu — keep data in local Excel / JSON
2. Use export_local_cache.py to export local cache
3. Use local_cache_reader.py for instant read access
```

### Q: All scores are C

```
Check product_profiles.json — is "active" pointing to the correct product profile?
If the profile doesn't match the search keywords, content fit scores will be at the floor (10 points),
resulting in all C grades.
Make sure the profile's "keywords" field covers the keywords used in search.
```

---

## Appendix: Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Complete Workflow Cheat Sheet              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Configuration                                       │
│  ┌──────────────────────────────────┐                       │
│  │ .env → YOUTUBE_API_KEY           │                       │
│  │ keyword.txt → one keyword/line   │                       │
│  │ product_profiles.json → profile   │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 2: Search                                              │
│  ┌──────────────────────────────────┐                       │
│  │ python main.py batch              │                       │
│  │   --keywords-file keyword.txt     │                       │
│  │   -o output/batch_1               │                       │
│  │   --sort-order relevance --yes    │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 3: Merge                                               │
│  ┌──────────────────────────────────┐                       │
│  │ python main.py merge-output       │                       │
│  │   output/batch_1 [output/batch_2] │                       │
│  │   -o output/summary/kol.xlsx      │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 4: Sync to Feishu                                      │
│  ┌──────────────────────────────────┐                       │
│  │ First time: sync_to_user_base.py │                       │
│  │ Later: write_user_base.py         │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 5: Detect Promo + Emails                               │
│  ┌──────────────────────────────────┐                       │
│  │ python refresh_promo_lark.py      │                       │
│  │ (requires YouTube API + proxy)    │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 6: Score                                               │
│  ┌──────────────────────────────────┐                       │
│  │ python score_influencers.py       │                       │
│  │ (reads Feishu only, no YT quota)  │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 7: Derived Table + Cache                               │
│  ┌──────────────────────────────────┐                       │
│  │ python build_hongren_table.py     │                       │
│  │ python export_local_cache.py      │                       │
│  └──────────────────────────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

- **Influencer Outreach**: After scoring, contact influencers in S → A → B priority order. Use the outreach skill to generate first-contact email templates.
- **Regular Refresh**: Re-run `refresh_promo_lark.py` weekly to capture new channels' promo experience and emails.
- **Expand Keywords**: When you discover new product-relevant keywords, run a separate `batch`, then `merge-output` with old directories.
- **Multi-Market**: Use different `--region` / `--lang` to search different markets (e.g., `--region DE --lang de` for Germany).

---

> Got issues? Just paste the error message to your AI assistant — it will diagnose and fix it for you.
