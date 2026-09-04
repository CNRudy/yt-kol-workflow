---
name: yt-kol-feishu-sync
description: >-
  YouTube KOL 网红开发工作流 → 飞书多维表格（Base）的端到端同步技能。
  当用户要"用关键词搜 YouTube 网红/视频并同步到飞书表格"、"配置飞书同步"、
  "重跑搜索后首轮数据会怎样"、"为什么我在 base 里没权限改字段/建视图"、
  "红人表有没有同步/怎么更新"、"主库为什么有重复/无来源记录"时启用。
  覆盖了：用户可在哪填参数、标准工作流步骤、第二次填关键词时首轮数据的命运，
  以及 lark-cli / 飞书字段格式 / 清空重写 vs 增量 upsert / 合并去重 / 授权流程 等踩坑点。
  也覆盖"邮箱抓不到"、"怎么判断红人有没有推过亚马逊/有没有带货经验"、
  "给存量红人回填推广经验和邮箱"（refresh_promo_lark.py）、
  "目标导向评分 S/A/B/C"（score_influencers.py + rescore_soccer.py）、
  "本地缓存秒级读取"（export_local_cache.py + local_cache_reader.py）、
  "红人表派生精简表"（sync_hongren_table.py，增量同步替代删表重建）。
agent_created: true
---

# YouTube KOL 工作流 → 飞书多维表格同步

> 本文件是唯一权威文档（AI 技术细节 + 命令全合一）。
> 面向使用者（怎么看飞书表、筛红人、各列含义、业务口径）的人读说明见
> 项目根 `YouTube 网红开发工作流系统/README.md`；
> 更早版本 / 历史交接文档已归档在项目根 `archive/`（含 8 月工作交接快照）。

把 `Saramusk/Youtube-Creator-Workflow`（YouTube 网红搜索）产出的 Excel 汇总表，
同步进**用户身份拥有的**飞书多维表格（Base），让用户拥有字段配置与建视图的完整权限。

## 0. 一句话架构

```
YouTube 搜索 (main.py batch)
   └─> output/<时间戳>_batch/  本地 Excel（按关键词分文件）
         └─> merge-output      合并去重成一个 kol_summary_tables.xlsx（4 张表）
               └─> 飞书同步     用「你的飞书身份」同步 → 你的可编辑 Base VyH0
                     │           ├─ main.py sync-workbook（增量 upsert，同步完自动带红人表）
                     │           └─ write_user_base.py（清空 4 表 + 重灌，大版本全量替换用）
                     └─> 补算   refresh_promo_lark.py（promo+邮箱）+ score_influencers.py / rescore_*.py（评分）
                           └─> 派生   sync_hongren_table.py（红人表增量同步）+ export_local_cache.py（本地缓存）
```

两条飞书写路径的取舍：
- **日常新增/小版本**：`main.py sync-workbook --workbook <xlsx>`（feishu/workbook_sync.py，**增量 upsert**：
  按 Channel ID 匹配，已有记录原地更新；且内置 `preserve_existing_nonblank` 保护人工列：
  联系邮箱/邮箱状态/开发状态/开发负责人/备注，主表为空或人工列已有值就不覆盖）。
  同步完主表后**自动增量同步红人表**（`--skip-hongren` 可跳过）。
- **大版本整表替换**（如换产品线全量重灌）：`write_user_base.py`（清空 4 表 + 重写，
  保留字段/视图；⚠️ 会丢逐行手填值，且会触发主表级全量写，谨慎用）。

## 1. 用户能填写 / 操控的部分

### A. 搜索阶段（在跑搜索前给定）
| 参数 | 怎么给 | 说明 |
|---|---|---|
| YouTube API Key | `.env` 的 `YOUTUBE_API_KEY` 或环境变量 | 必需 |
| 关键词 | 关键词文件（`batch` 的 `--keywords-file`）或交互输入 | 如 `toddler gear`、`amazon baby products` |
| 每个词最大结果数 | 关键词文件里 `关键词,数量` 或 `--max-results`（默认 100） | 影响配额 |
| 地区 / 语言 | `--region`（默认 US）/ `--lang`（默认 en） | |
| 过滤条件 | `--min-views`(默认1万) / `--min-engagement`(默认3.0) / `--min-subscribers` / `--filter-mode` | 筛掉低质频道 |
| 输出目录 | `--output-dir` / `-o` 或环境变量 `OUTPUT_DIR` | **重要**：决定数据是否跨轮合并（见第 3 节） |

### B. 飞书同步阶段
| 可操控项 | 说明 |
|---|---|
| 目标 Base | 用「你的身份」建的 Base（你是 owner）。`BASE_TOKEN = <FEISHU_BASE_TOKEN>` |
| 表名映射 | `write_user_base.py` 的 `SHEETS`：xlsx sheet → 飞书表名；`TABLE_IDS` 存 tbl 开头的真实表 ID |
| 字段类型推断规则 | `infer_type()`：URL 列→url、日期列→date、数字列→number、指定列→select、其余→text |
| 单选列白名单 | `SELECT_COLS`：断更评估/国家/地区/邮箱状态/邮箱来源/亚马逊推广经验/开发优先级/开发状态/来源关键词 |
| 强制类型 | `FORCE_TYPES`：推广链接/推广证据/候选邮箱/推荐理由/匹配关键词/内容契合类型→text；品牌匹配度/Amazon Storefront→url 或 number |

### C. 用户在飞书界面里能做的（正因为这 Base 是你建的）
- 改字段配置（加/删字段、改类型、给单选加选项、调顺序）
- 建任意视图（筛选 / 分组 / 排序 / 看板）
- ⚠️ 逐行手填的「人工列」（备注/开发状态/联系邮箱/开发负责人/开发优先级）：
  **sync-workbook 与 sync_hongren_table.py 都会保护它**（红人表/主表已有值不覆盖）；
  但 **write_user_base.py 清空重灌会丢**（见第 3 节 + 注意事项）

## 2. 标准工作流（第一次）

```bash
REPO=".../YouTube 网红开发工作流系统"
cd "$REPO/assets/yt-kol-workflow"

# 1) 配 .env：YOUTUBE_API_KEY、飞书套件已连接（lark-cli --as user 可用）
# 2) 跑批量搜索（结果进 output/<时间戳>_batch/）
python main.py batch --keywords-file keywords.txt -o output/<时间戳>_batch
#    或交互：python main.py search --keyword "toddler gear"

# 3) 合并成一个汇总表（4 张表，按 Channel ID 去重）
#    注意：batch_dirs 是位置参数，不是 --batch-dirs
python main.py merge-output output/<时间戳>_batch \
    -o output/summary_<时间戳>/kol_summary_tables.xlsx

# 4a) 日常同步（推荐）：增量 upsert + 同步完自动更新红人表
python main.py sync-workbook --workbook output/summary_<时间戳>/kol_summary_tables.xlsx \
    --feishu-app-token <FEISHU_BASE_TOKEN>
#    （--skip-hongren 可跳过红人表自动同步）

# 4b) 或大版本整表替换（清空重灌 4 表）
python write_user_base.py

# 5) 补算 promo + 邮箱（走 YouTube API 抓视频描述，需翻墙代理，必须后台跑）
./.venv/bin/python refresh_promo_lark.py

# 6) 补算评分（只读飞书，不耗 YouTube 配额）
./.venv/bin/python score_influencers.py

# 7) 刷新本地缓存（写飞书后必跑，否则分析脚本读旧数据）
./.venv/bin/python export_local_cache.py
```

**⚠️ 环境前置（每次跑飞书写操作前都必须做，详见踩坑 20/21/22）**：
```python
# lark-cli 真实路径（write_user_base.py 顶部常量已指向失效的 node/22.22.2 目录，必须运行时覆盖）
wb.LARK = "/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"   # Clash HTTP 代理（翻墙写飞书不是必须，但保险）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["LARK_CLI_NO_PROXY_WARN"] = "1"
```

## 2.5 邮箱抓取 & 亚马逊推广经验判定（2026-07-31 重做，2026-08-14 修订）

### 为什么早期版本邮箱抓得少
旧逻辑只从**频道简介**（`channels.list` 的 `snippet.description`）正则抽邮箱。
但 YouTube 的"关于"页商务邮箱藏在验证码后面，**API 永远拿不到**；
绝大多数创作者其实把商务邮箱写在**每条视频的描述**里。
而 `videos.list` 的 `snippet.description` 我们本来就在抓（同一次请求、零额外配额）。

### 现在的做法
| 模块 | 作用 |
|---|---|
| `filter/email_extractor.py` → `extract_contact_email(channel_desc, video_descs)` | 频道简介 + N 条视频描述一起抽；**按跨视频出现频次排序**（赞助商邮箱只出现 1 次，本人商务邮箱几乎每条视频都有）；过滤 amazon/youtube/epidemicsound 等平台噪音域名和 `logo@2x.png` 这类假邮箱 |
| `filter/promo_detector.py` → `detect_video_promo` / `aggregate_channel_promo` | 从视频描述里识别亚马逊/联盟推广痕迹并分级 |

**推广经验分级**（由高到低，写进「亚马逊推广经验」单选列）：
1. `Amazon Storefront` — 命中 `amazon.<tld>/shop/<handle>`，说明已加入 Amazon Influencer Program，价值最高
2. `Amazon 联盟客` — Amazon 链接上带 `?tag=xxx-20`，或有 "As an Amazon Associate" 声明
3. `挂过Amazon链接` — 有 `amzn.to` / `a.co` / `amazon.*/dp/` 等链接
4. `其他联盟带货` — geni.us / LTK / ShopMy / 通用 affiliate 措辞
5. `接过赞助` — 只有 `#ad` / `paid promotion` / `sponsored by`
6. `未发现`

⚠️ `tag=` 只有出现在 **Amazon 域名的 URL 上**才算联盟 ID，别的站点 `?tag=` 是普通分类参数。

### 新增字段
- 网红详情表：`邮箱来源`(单选) / `邮箱出现视频数` / `候选邮箱` / `亚马逊推广经验`(单选) / `Amazon带货视频数` / `推广视频数` / `Amazon Storefront`(URL) / `推广证据`
- 网红视频表：`推广类型` / `推广链接`（定位到具体是哪条视频挂的链接）

### 每频道抓的视频数 10 → 25
`run_phase_d(recent_video_count=25)`。**配额不变**：`playlistItems.list` 一页最多 50 条算 1 unit，
`videos.list` 每 50 个 ID 算 1 unit，所以 25 条和 10 条都是每频道 2 units。
但样本从 10 条涨到 25 条，邮箱和推广链接的命中率大幅提高。代价只是「网红视频表」行数变 2.5 倍。

### 给存量红人回填 promo + 邮箱（⚠️ 用 refresh_promo_lark.py，别用 main.py refresh）

⚠️ **`main.py refresh-influencers --fields promo` 已废弃**：它走 `feishu/bitable.py` 的**应用身份**鉴权，对该 Base 报 `code=10014 app unauthorized`，写不进去。`.env` 里 `FEISHU_APP_TOKEN` 缺失、`FEISHU_APP_ID/SECRET` 对该 Base 未授权。

**用 `refresh_promo_lark.py` 代替**（走 lark-cli 用户身份 + YouTube API 抓描述 + 硬编码翻墙代理）：

```bash
cd ".../assets/yt-kol-workflow"

# 全量补算（跳过已处理频道，支持断点续传）
./.venv/bin/python refresh_promo_lark.py

# 只跑 N 个（测试用）
./.venv/bin/python refresh_promo_lark.py --limit=5

# 只看不写
./.venv/bin/python refresh_promo_lark.py --dry-run
```

- 脚本逻辑：按频道拉最近 25 条视频描述 → `aggregate_channel_promo` + `extract_contact_email` 计算 → `lark-cli +record-upsert` 写回网红详情表
- **已有邮箱的行不会被覆盖**，只补空的
- **断点续传**：跳过已填好「亚马逊推广经验」的频道，重跑只补未处理的，不浪费 YouTube 配额
- 配额：每频道约 2 units，500 个红人约 1000 units（日配额 10000）
- 脚本内置 `ensure_fields()` 用不带 `--yes` 的 `field-create` 自建 8 个 promo/邮箱字段（绕开 ensure_schema 的 --yes bug）
- ⚠️ **必须后台运行**（`run_in_background: true` + `dangerouslyDisableSandbox: true`），前台会被 SIGKILL
- ⚠️ **后台任务有运行时长上限**（约 20 分钟被回收），500 个频道约 30 分钟会被中断，重跑接上即可（断点续传）
- 代理：脚本自动读 `HTTPS_PROXY` 环境变量，回退到显式 `http://127.0.0.1:7890`（Clash HTTP）。
  曾经的 `socks5h://127.0.0.1:10808` 已废弃（端口未开放）。

## 2.6 目标导向评分层

### 产品画像配置
`product_profiles.json`：按产品配置画像，`active` 指定当前用哪个。
**当前（2026-09）active = `baby_car_camera_us`**（WEMOH C1 婴儿车载摄像头）。
已配置画像（6 个）：`baby_car_camera_us` / `magnetic_baby_car_camera_de`（德语）/
`youth_soccer_shin_guard`（足球护膝）/ `airtag_passport_holder`（Stouchi AirTag 护照包, CFC1）/
`mac_mini_dock` / `apple_accessory`（Stouchi 3C）。

```json
{
  "active": "baby_car_camera_us",
  "profiles": {
    "youth_soccer_shin_guard": {
      "name": "适合 18 岁以下的足球护膝(Shin Guards)",
      "keywords": ["soccer","shin guard","shin guards","youth soccer","soccer gear",...],
      "content_types": ["评测","开箱","使用体验","种草","训练"],
      "markets": ["US"],
      "min_views": 20000,
      "min_engagement": 1.5
    }
  }
}
```

### 评分逻辑
| 模块 | 作用 |
|---|---|
| `filter/scoring.py` → `score_influencer(detail, videos, profile)` | 返回 7 字段：匹配产品 / 品牌匹配度(0-100) / 内容契合类型 / 匹配关键词 / 开发优先级(S/A/B/C) / 推荐理由 / 匹配排序组 |
| `score_content_fit` | 视频标题/Tags/描述匹配产品关键词 → 0-100 分 |
| `score_business` | 亚马逊推广经验 + 邮箱 + 互动率 + 持续更新 → S/A/B/C + 推荐理由 |

### 评分写回
| 脚本 | 用途 |
|---|---|
| `score_influencers.py` | 全表补算（读网红视频表+详情表 → 写回 6 列；断点续传：跳过已填「开发优先级」的频道） |
| `rescore_<产品>.py`（如 rescore_soccer.py） | 定向重算某批（如匹配产品为空的 352 条足球），传目标画像显式评分，不覆盖人工列 |
| `match_full_table.py` | 整表匹配（读本地缓存 + 飞书 → 算 7 字段 → 输出 xlsx / push 回飞书） |

```bash
# 预览（只读飞书，不写）
./.venv/bin/python score_influencers.py --dry-run
# 写回飞书
./.venv/bin/python score_influencers.py
```
- 只读飞书（网红视频表 + 网红详情表），**不耗 YouTube 配额**
- 内置 `ensure_score_fields()` 用不带 `--yes` 的 `field-create` 自建评分列
- `run_long()`：300s 超时（替代 `run()` 的 120s）+ 3 次重试 + try/except
- ⚠️ **必须后台运行**（长任务，约 8-10 分钟跑 500 个频道）

### 评分前必做
跑评分前先确认 `product_profiles.json` 的 `active` 设成与该批搜索匹配的产品画像。
不匹配会导致全 C（内容契合度=10 地板分）。**传入 profile 优先级高于 active**：
`score_influencer(detail, videos, profile)` 显式传 profile 可避免误用当前 active。

### 已知质量缺陷（2026-09 实测）
- 关键词偏"产品词"（如 shin guards），而足球频道内容多是泛足球 → **37% 得 0 分、平均 10.4 分**，
  连 54.8 万订阅的 SOCCSTER 都只得 10 分。需补泛类目关键词或放宽市场/门槛后再重跑。

## 2.7 本地缓存

飞书 API 分页拉全表要 30+ 次调用、耗时 3 分钟。本地缓存 **0.066 秒**读完，提速 ~2700 倍。

### 导出 / 刷新
```bash
# 全量导出（注意：EXTRA_TABLES 里的 soccer_scores 已删表，全量会报错 → 见下）
./.venv/bin/python export_local_cache.py

# 单表导出（推荐，避开已删表）
./.venv/bin/python export_local_cache.py influencers
./.venv/bin/python export_local_cache.py hongren

# 查看可用表
./.venv/bin/python export_local_cache.py --list
```

⚠️ **跑之前必须**（export_local_cache.py 顶层 `import dotenv` 但 venv 没装 python-dotenv）：
```python
# 方式一（推荐）：pip install python-dotenv
# 方式二（stub 绕过，不改环境）：
import sys, os, types
_m = types.ModuleType("dotenv"); _m.load_dotenv = lambda *a, **k: None
sys.modules["dotenv"] = _m
```
同时需覆盖 `wb.LARK` 为真实路径（见标准工作流的环境前置）。`sync_hongren_table.py` 已内置以上 stub + LARK 覆盖，可直接 `python sync_hongren_table.py`。

⚠️ **`export_local_cache.py` 的 EXTRA_TABLES 仍引用已删除的足球评分表**
`soccer_scores`（tble06acWNOPB6vX）——全量导出会因该表不存在而报错。**只导出存在的表**
（influencers / hongren / videos / channel_videos / search_tasks），或先删掉 EXTRA_TABLES 里的 soccer_scores 行。

### 读取（后续脚本优先用本地缓存）
```python
from local_cache_reader import load_influencers, video_map_by_channel

details = load_influencers()        # 1821 条，秒级
vmap = video_map_by_channel()       # {channel_id: [video_dict, ...]}
```

### 缓存文件（local_cache/ 目录，最近导出 2026-09-04）
| 文件 | 记录数 | 对应飞书表 | 导出时间 |
|---|---|---|---|
| `influencers.json` | 1821 | 网红详情表（主库，已去重） | 2026-09-04 ✅最新 |
| `hongren.json` | 1505 | 红人表（派生） | 2026-08-17 ⚠️落后 |
| `videos.json` | 5258 | 视频数据表 | 2026-08-17 |
| `channel_videos.json` | 5984 | 网红视频表 | 2026-08-04 |
| `search_tasks.json` | 29 | 搜索任务表 | 2026-08-17 |

⚠️ 缓存需手动刷新：每次补算/写入飞书后跑一次 `python export_local_cache.py influencers`。
评分脚本如需要视频数据且缓存较旧（如 8/4），先确认覆盖率再决定是否刷 channel_videos。

## 2.8 红人表派生精简表（sync_hongren_table.py — 2026-09 取代 build_hongren_table.py）

用户要求从网红详情表派生一个精简表（25 列）。**过去靠 `build_hongren_table.py`「删旧表再建」→ 每次更新 table_id 会变、飞书链接失效、无法自动同步。**

### 新做法：增量 upsert，不删表
```bash
# 预览同步计划（只读不写）
./.venv/bin/python sync_hongren_table.py --dry-run
# 执行同步（新增缺失行 + 更新有差异字段）
./.venv/bin/python sync_hongren_table.py
# 额外清理重复 Channel ID 的多余行（先合并独有人工数据、成功才删）
./.venv/bin/python sync_hongren_table.py --dedupe
```

核心特性：
- **不删表、不重建 → table_id 永久固定**（`tblPKFENcpk8xnZH`），飞书链接/视图不失效
- 按 Channel ID 做增量 upsert（读主表网红详情表全量 → 对比 → 只写有差异的）
- **保护人工维护列** `MANUAL_COLS = {备注, 开发状态, 联系邮箱, 开发负责人, 开发优先级}`：
  红人表已有值时不被主表覆盖（否则 103 条"已联系"会被回退成"待联系"）
- **主表为空的值不写入**，绝不清除红人表已有内容
- 字段类型以红人表**实际 schema** 为准（动态读取，不硬编码）
- 数字比较注意：int/float 统一按 `float(x):.6g` 格式化，否则飞书返回 int(1140000)
  与写入 float(1140000.0→"1.14e+06") 会误判为差异 → 每次重复更新（假差异 bug，已修）
- select/单选值传 plain string（非数组）；空值传 None（不能传 `''`，否则批量创建 not_found）
- 内置 stub dotenv + LARK 覆盖（可直接 `python` 运行，无需手动设环境）
- 删除记录需要 `--yes`（lark-cli 高风险写保护）

### 嵌入 sync-workbook（2026-09-03）
`main.py sync-workbook` 同步完主表（`--table influencers` / `all`）后**自动**增量同步红人表：
```bash
python main.py sync-workbook --workbook <xlsx> --feishu-app-token VyH0...   # 自动带红人表
python main.py sync-workbook --workbook <xlsx> --skip-hongren               # 跳过红人表
```
红人表同步失败**不影响**主表同步结果（异常已捕获，只打印警告）。

### 去重（sync_hongren_table.py --dedupe / clean_main_dupes.py）
- 主表曾因足球关键词批次被重复导入，产生 **297 个重复 Channel ID**（主表 2118 → 1821 行）
- `clean_main_dupes.py`：清主表重复（每组保留信息最全的一条 + 先备份到 `output/backup/`）
- 红人表去重由 `sync_hongren_table.py --dedupe` 完成，删除前**先合并人工数据到保留行、成功才删**
- 曾拦下 3 条会丢失的人工备注（"报价 100 刀，适合足球类"等），抢救回表

## 2.9 主库现状速览（2026-09-04 实测）

| 项 | 值 |
|---|---|
| 主表（网红详情表）总行数 | **1821**（唯一 Channel ID 1821，重复 0） |
| 匹配产品分布 | WEMOH C1 婴儿车载摄像头 **1129** / 足球护膝 **352** / AirTag 护照包(CFC1) **340** / 空 0 |
| 来源关键词 | 56 个关键词全覆盖，空来源 = 0 |
| 红人表 | 1821 行，与主表 Channel ID 完全一致 |
| 人工数据 | 已联系 103 条 / 备注 42 条 / 联系邮箱 604 条 |

VyH0 Base 现有 **6 张表**（见第 6 节映射）。CFC1 是独立 Base（<FEISHU_BASE_TOKEN_CFC1>），
其数据可同步进主库（vyh0_sync_cfc1.py，340 条）。

## 3. 第二次填关键词时，第一次的数据会怎样？

**关键在 `output_dir` 和「合并时传了哪些 batch_dir」。**

| 你怎么做 | 首轮数据在 Base 里的结果 |
|---|---|
| 把首轮+二轮**所有关键词放进同一次 `batch`** | ✅ 首轮数据全保留（一次合并去重）；⚠️ 但**首轮关键词会被重新搜索一遍**，每词照常消耗 `search.list` 配额（约 100/词），且代码里**没有"关键词已搜过就跳过"的缓存。频道级去重（seen_channels.json + 飞书已有 Channel ID）保证不会重复计网红，视频是 upsert 不会重复行。 |
| 二轮用**新 output_dir**，且 `merge-output` 只传二轮目录 | ❌ 首轮**从 Base 消失**（若走 write_user_base 清+重灌只含二轮；走 sync-workbook 增量 upsert 则仍在）。首轮文件仍在磁盘旧目录，只是没被合并 |
| 二轮用**新 output_dir**，但 `merge-output 旧目录 新目录`（位置参数）两个都传 | ✅ 首轮+二轮合并，去重后全保留 |
| 二轮**复用同一 output_dir** | 取决于 BatchExcelExporter 是否追加；默认每轮重写该目录汇总，**首轮可能被覆盖**（除非关键词含首轮） |

**结论 / 推荐做法**：
- 想要历史累计 → **不要合并关键词文件**，单独用新关键词跑 `batch`，再每次 `merge-output` 都把历次 `output/<时间戳>_batch` 目录**一起传**（按 Channel ID 去重，跨词不重复）。
- ⚠️ 避免把首轮关键词塞回新一次的 `batch`：首轮数据虽靠去重不丢，但首轮关键词会被**重新搜索**、白费配额（`search.list` 最贵）。正确做法是"关键词只搜一次，跨轮累计靠 merge-output 目录合并"。
- 合并按 **Channel ID 去重**，同一网红跨词出现不会重复。
- 飞书侧 `write_user_base.py` 是「清空重灌」；**增量维护（评分/回填/匹配）应走定向脚本 + upsert**，
  不要每次都用清空重灌。字段配置和视图**始终保留**（脚本只动记录，不动结构）。

## 4. 踩坑清单（必看）

### 环境 / lark-cli 二进制 / 授权（2026-09 最新）
1. **lark-cli 真实路径**：`/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli`。
   `write_user_base.py` 顶部常量仍指向已失效的 `node/versions/22.22.2/bin/lark-cli`（该 node 目录被清理）。
   **所有飞书写操作前必须设 `wb.LARK = <真实路径>`**，否则报 token_missing / 路径不存在。
2. **user token 失效授权流程**：旧 user token 丢失后，
   `lark-cli auth login --domain base --no-wait --json` 取 `device_code`+二维码给用户扫码；
   **必须**再 `lark-cli auth login --device-code <code> --json` 完成捕获
   （仅 `--no-wait` 先返回会丢 token，auth status 仍 `user: missing`）。
   `base:field:create` / `base:record:create` / `base:record:update` 均在 `--domain base` 授权范围内。
3. **子命令带 `+` 前缀**：lark-cli 的 base 操作实际子命令是 `+record-list` / `+field-list` /
   `+table-list` / `+record-batch-create` / `+record-batch-update` / `+record-delete` /
   `+table-create`（不带 `+` 的老名字可能 404 或返回空）。`base --help` 里能看到带 `+` 的项。
4. **`record-delete` / `+table-delete` 需要 `--yes`**（lark-cli 高风险写保护），否则被安全机制拦截。
5. **`record-batch-update` 格式（2026-09-02 确认）**：
   `--json '{"update_records":{"recA":{"字段名":"值"},...}}'`，每批≤200 条；text 字段直接传字符串。
6. **`record-batch-create` 是矩阵格式**：`--json '{"fields":[...列名], "rows":[[...],...]}'`。
   `record-upsert` 用 `--record-id` + flat field map（不包 fields）。
7. **`record-list` / `field-list` 返回结构**：`data.fields` = 列名数组、`data.data` = 行值数组、
   `data.record_id_list` = 记录 ID（三数组按索引对齐）。`+field-list` 的字段名在 `data.fields[].name`
   （不是 `field_name`）。
8. **分页：用 `--offset` + `--limit`，别用 `--page-token`**（has_more=True 时 page_token 仍是 None）。
   `record-list` 无 total 字段，要全量需循环直到返回行数 < limit。
9. **权限根因**：用「应用身份(tenant token)」建的 Base，你只是可阅读、没法改字段/建视图。
   解决：用**飞书套件（你的身份，`lark-cli --as user`）**建 Base，你就是 owner。
10. **`main.py refresh --fields promo` 写不进飞书**：走应用身份鉴权，报 `10014 app unauthorized`。用 `refresh_promo_lark.py` 代替（走 lark-cli 用户身份）。
11. **`ensure_schema` 给 `field-create` 传了 `--yes` → 字段从未被创建**：lark-cli `field-create` 不支持 `--yes`（报 unknown flag）→ 静默失败 → schema.py 设计的 39 字段实际只有 21 个落地。`refresh_promo_lark.py` 和 `score_influencers.py` 已各自内置不带 `--yes` 的建字段逻辑。
12. **lark-cli `--json` 不支持绝对路径**：必须 `@./相对名.json`（脚本同目录）。内联字符串超命令行长度上限（1450 行会炸），务必写文件 + `@相对路径`。
13. **建表时默认空表会被自动删**：`+base-create --table-name X` 会先建一个默认表再被替换，正常现象。
14. **飞书字段格式（裸 REST 时）**：建表 body 是 `{"table":{"name":...}}`；日期值是裸整数毫秒；URL 值是 `{"text","link"}`；数字必须 float；single_select 选项只能建字段时内嵌（事后加选项接口 404）。用 `lark-cli` 写记录时更简单：URL 列当 `text(style=url)`、数字当 `number`、日期当 `datetime` 字符串、单选直接带 `options`。
15. **清空是最终一致**：删记录后立刻 list 可能还读到旧数据，清表要循环「列举→删除」直到连续两次读到 0。
16. **select 字段值以 list 返回**（如 `['US']`），统计/Counter 前先 `_str()`/`norm()` 展平。
17. **select 空值必须传 `None`**，不能传 `''`（否则批量创建 not_found）。
18. **select 字段选项缺失**：新关键词/国家不在飞书表选项里会报 not_found。需用 `+field-update`
    （PUT 语义、**全量选项**）补全，格式 `name/type/multiple/options` 完整结构 + `--yes`。
    单选选项加颜色用 `hue`（Red/Gray 等）+ `lightness`（必须 Standard/Lighter，非 Normal）。
    `来源关键词` 用名字更新 OK；`国家/地区` 用名字更新 404，需用字段 ID（`flddXjEdHW`）。
19. **`record-batch-create` / `record-delete` 必须用 `tbl` 开头的真实表 ID**，用表名会 not_found。
    表 ID 存 `write_user_base.py` 的 `TABLE_IDS` 字典。
20. **lark-cli 错误 JSON 走 stderr**，成功走 stdout；`run()` 要同时检查两个流（优先 stdout，
    空则回退 stderr，且要过滤非 JSON 行找第一行 JSON）。
21. **`run()` 硬编码 `timeout=120`**，不支持传参。长操作用 `score_influencers.py` 里的 `run_long()`（300s 超时 + 3 次重试）。
22. **sandbox 阻断 `os.remove`** 临时文件，改为覆盖不删。设 `LARK_CLI_NO_PROXY_WARN=1` 抑制 lark-cli proxy 警告污染 stdout。
23. **`export_local_cache.py` 顶层 `import dotenv` 但 venv 没装 python-dotenv** → 直接跑 ModuleNotFoundError。
    用 stub 绕过（见 2.7）或 `pip install python-dotenv`。EXTRA_TABLES 残留已删 soccer_scores 表，全量导出会报错，只导存在的表。
24. **数字比较假差异**：飞书返回 int(1140000)，本地写入 float(1140000.0)；比较前统一
    `f"{float(v):.6g}"` 格式化，否则每次同步都重复更新同一批行。
25. **`present_files` 会把 `.csv` 转成 xlsx(zip)** 写回磁盘（后缀仍是 .csv，内容变 `PK\x03\x04`）。别对还要程序读取的 .csv 调 present_files。
26. **还原/清洗脚本的关键词白名单必须与各批次实际搜索关键词同步**：曾因白名单只覆盖 19 个早期词、
    漏掉 8/26 批次英文婴儿车词，把 273 条有来源记录误清成"无来源"（restore_nosource.py 已按
    batch Excel 反查补回）。导入飞书时务必校验「来源关键词」不丢失。

### YouTube API / 代理相关
27. **YouTube API 拿不到邮箱**（关于页验证码）；邮箱只能从视频描述抽。
28. **代理 = Clash HTTP `http://127.0.0.1:7890`**（或读环境变量 HTTPS_PROXY/HTTP_PROXY）。
    **`socks5h://127.0.0.1:10808` 已废弃（端口未开放）**，不要再用。sandbox 后台不继承命令行
    HTTPS_PROXY 前缀；环境 HTTP_PROXY=61210 是 WorkBuddy 内网代理不能翻墙 → 显式设/传 proxies。
29. **带网络的后台脚本前台跑会被 SIGKILL**（整个 shell 被杀），必须 `run_in_background: true` + `dangerouslyDisableSandbox: true`。
30. **后台任务有运行时长上限**（约 20 分钟被回收）。长任务（500 频道约 30 分钟）会被中断，
    脚本需支持断点续传，重跑接上即可。

## 5. 衍生脚本位置（项目内）
- `assets/yt-kol-workflow/main.py`：搜索 / 合并 / sync-workbook 入口（含 --skip-hongren）
- `assets/yt-kol-workflow/sync_to_user_base.py`：首次建 Base+4 表（用户身份，只跑一次）
- `assets/yt-kol-workflow/write_user_base.py`：清空+重写数据（大版本全量替换用；含 BASE_TOKEN/TABLE_IDS/SELECT_COLS/FORCE_TYPES）
- `assets/yt-kol-workflow/feishu/workbook_sync.py`：sync-workbook 的增量 upsert 引擎（preserve_existing_nonblank 保护人工列）
- `assets/yt-kol-workflow/refresh_promo_lark.py`：补算 promo+邮箱（lark-cli 用户身份 + 代理 + 断点续传）
- `assets/yt-kol-workflow/score_influencers.py`：离线评分写回 6 列（run_long 300s + 断点续传；含 list_all 通用读取器）
- `assets/yt-kol-workflow/rescore_soccer.py`：定向重算足球护膝（352 条空匹配产品补算）
- `assets/yt-kol-workflow/sync_hongren_table.py`：红人表派生精简表增量同步（不删表、保护人工列、--dedupe）
- `assets/yt-kol-workflow/clean_main_dupes.py`：主表重复 Channel ID 清理（先备份，保留信息最全一条）
- `assets/yt-kol-workflow/restore_nosource.py`：无来源记录按 batch 反查补回（关键词白名单教训）
- `assets/yt-kol-workflow/match_full_table.py` / `push_match_to_feishu.py`：整表匹配评分 + 写回飞书
- `assets/yt-kol-workflow/vyh0_sync_cfc1.py` / `vyh0_rescore_cfc1.py`：CFC1 独立 Base → 主库同步/重算
- `assets/yt-kol-workflow/build_hongren_table.py`：❌ 旧红人表生成（删表重建）——已被 sync_hongren_table.py 取代，勿再用
- `assets/yt-kol-workflow/export_local_cache.py`：一键导出飞书表到本地 JSON 缓存（需 stub dotenv）
- `assets/yt-kol-workflow/local_cache_reader.py`：本地缓存秒级读取器
- `assets/yt-kol-workflow/product_profiles.json`：产品画像配置（当前 active = baby_car_camera_us，共 6 画像）
- `assets/yt-kol-workflow/feishu_sync_v2.py`：旧「应用身份」同步脚本（已弃用，仅只读备份 JB3 base 用）

## 6. 飞书表 ID 映射（VyH0 Base，2026-09-04 实测 6 张表）
| 表 | table_id | 记录数 | 备注 |
|---|---|---|---|
| 网红详情表 | `tbl4rnFUM9jJXvCQ` | 1821 | 主库核心全量表，含 promo/邮箱/评分列（7 字段：匹配产品/品牌匹配度/内容契合类型/匹配关键词/开发优先级/推荐理由/匹配排序组） |
| 视频数据表 | `tblDQi8dEGhkjZyy` | 5258 | 含 `描述` 字段 |
| 网红视频表 | `tblcHBORC90WWn05` | 5984 | 每频道 N 条，存储大头（22129 曾超限，见下） |
| 搜索任务表 | `tblLT1yf9ioEhJOh` | 29 | 每次搜索 1 行 |
| 红人表（派生） | `tblPKFENcpk8xnZH` | 1821 | 25 字段精简表，增量同步，table_id 永久固定 |
| 红人表 maa 全表匹配 | `tblyy7XAfBhFdw5y` | — | 25 字段，另一份全表匹配结果副本（8 月全表匹配） |

> 注 1：soccer_scores（tble06acWNOPB6vX）已删除——数据并入网红详情表评分列，export_local_cache.py 的 EXTRA_TABLES 里残留其引用需清理。
> 注 2：**网红视频表有行数上限坑**：曾达 22129 行超限（code 800040832），用户决定此类大表不同步、放本地。
> 注 3：CFC1 独立 Base `<FEISHU_BASE_TOKEN_CFC1>`（tblpAZFZ5KWywucp）340 条，数据已同步进主库。

## 注意事项
- 用户若在 Base 里**逐行标注**（如把开发状态改成"已联系"），sync-workbook / sync_hongren_table
  的 **upsert 模式会保护人工列**（红人表已有值不覆盖）。只有 `write_user_base.py` 清空重灌会丢——
  大版本替换前先确认或备份。
- **写飞书后必跑 `export_local_cache.py influencers` 刷新本地缓存**，否则后续脚本读到的是旧数据。
- 增量/评分/匹配脚本优先读本地缓存（秒级），写飞书用定向 upsert；**不要每次都用清空重灌**。
