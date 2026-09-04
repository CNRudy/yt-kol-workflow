# AI 交接文档 · YouTube 网红开发工作流系统

> **用途**：给新对话（AI）直接当上下文。包含全部技术细节、代码路径、表 ID、已知坑、运行命令。
> **最新技术细节以 skill `yt-kol-feishu-sync` 的 `SKILL.md` 为准**，本文件是其项目内镜像。
> **人读使用说明**（业务视角）见同目录 `使用说明与注意事项.md`。
> 上次更新：2026-09-04。

---

## 0. 一句话定位

用关键词搜 YouTube 网红和视频 → 落库 → 同步到飞书多维表格（Base） → 给每个红人做
「品牌匹配度 + 开发优先级（S/A/B/C）」评分 → 派生精简「红人表」 → 辅助亚马逊站外推广选人。

代码目录：`/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow/`

---

## 1. 系统架构（2026-09 现状）

```
YouTube 搜索 (main.py batch)
   └─> output/<时间戳>_batch/  本地 Excel（按关键词分文件）
         └─> merge-output      合并去重成一个 kol_summary_tables.xlsx（4 张表）
               └─> 飞书同步     用户身份 lark-cli → Base VyH0
                     │           ├─ main.py sync-workbook（增量 upsert + 自动同步红人表）
                     │           └─ write_user_base.py（清空 4 表 + 重灌，大版本替换用）
                     └─> 补算   refresh_promo_lark.py（promo+邮箱，YouTube API + Clash HTTP 代理）
                           │    score_influencers.py / rescore_*.py（评分，只读飞书不耗 YouTube 配额）
                           └─> 派生   sync_hongren_table.py（红人表增量同步，不删表）
                                 export_local_cache.py（本地缓存，后续脚本秒级读取）
```

两条飞书写路径：
- **日常/增量**：`main.py sync-workbook --workbook <xlsx> --feishu-app-token VyH0...`
  → feishu/workbook_sync.py 增量 upsert，按 Channel ID 匹配，`preserve_existing_nonblank`
  保护人工列（联系邮箱/邮箱状态/开发状态/开发负责人/备注）；同步完主表自动增量同步红人表
  （`--skip-hongren` 可跳过）。
- **大版本整表替换**：`write_user_base.py`（清空 4 表 + 重写，保留字段/视图；⚠️ 丢逐行手填值）。

---

## 2. 已完成工作清单

### ① 邮箱抓取重做 + 亚马逊推广经验自动判定（2026-07-31，08-14 修订）
- `filter/promo_detector.py`：`aggregate_channel_promo(videos)` → 分级
  Amazon Storefront > Amazon 联盟客 > 挂过Amazon链接 > 其他联盟带货 > 接过赞助 > 未发现。
- `filter/email_extractor.py`：频道简介 + 25 条视频描述多源抽取，按跨视频出现频次识别本人邮箱。
- 每频道抓视频数 10 → 25（配额不变，每频道仍 2 units）。
- ✅ 主库 1821 个频道已全部补填。

### ② 目标导向评分层
- `product_profiles.json`：6 个画像。**当前 active = `baby_car_camera_us`**（WEMOH C1 婴儿车载摄像头）。
- `filter/scoring.py`：`score_content_fit`(0-100) + `score_business`(S/A/B/C+推荐理由) +
  `score_influencer`(整合返回 7 字段：匹配产品/品牌匹配度/内容契合类型/匹配关键词/开发优先级/推荐理由/匹配排序组)。
- `score_influencers.py`：离线存量补算（run_long 300s + 断点续传）。
- `rescore_soccer.py`：定向重算足球护膝（352 条空匹配产品，用 youth_soccer_shin_guard 画像）。

### ③ 红人表派生精简表（2026-09 起用 sync_hongren_table.py 增量同步）
- ✅ `sync_hongren_table.py`：**不删表**的增量 upsert（新增缺失行 + 更新有差异字段），
  table_id 永久固定 `tblPKFENcpk8xnZH`，支持 `--dedupe` 清理重复 Channel ID。
- **保护人工列** MANUAL_COLS = {备注, 开发状态, 联系邮箱, 开发负责人, 开发优先级}：红人表已有值不覆盖。
- **主表为空的值不写入**，绝不清除红人表已有内容。
- 数字比较统一 `f"{float(v):.6g}"` 防 int/float 假差异（已修）。
- ❌ `build_hongren_table.py`（删表重建）已弃用。
- 嵌入 `main.py sync-workbook`：同步完主表自动带红人表（`--skip-hongren` 可关）。

### ④ 主表去重（2026-09-03）
- 根因：足球关键词批次被重复导入，主表 297 个重复 Channel ID（2118 → 1821 行）。
- `clean_main_dupes.py`：清主表重复（每组保留信息最全一条，先备份 output/backup/）。
- 红人表去重：`sync_hongren_table.py --dedupe`（先合并独有人工数据、成功才删）。
- 拦下 3 条会丢失的人工备注并抢救回表。

### ⑤ 无来源记录修复（2026-09-03）
- 8/26 英文婴儿车批次导入时「来源关键词」未写入 + 还原脚本白名单漏词 → 273 条被误清成"无来源"。
- `restore_nosource.py`：从 batch Excel 反查来源关键词（补 7 个英文选项）+ 从 8 月全表匹配 Excel
  取 6 个匹配字段 → 273/273 回填 WEMOH C1。

### ⑥ 本地缓存基础设施
- `local_cache/` 目录：全量飞书表 JSON 副本。网红详情表 1821 条（2026-09-04 刷）。
- `export_local_cache.py`：一键导出/刷新。⚠️ 顶层 `import dotenv` 但 venv 未装 python-dotenv，
  需 stub 或 pip install；EXTRA_TABLES 残留已删 soccer_scores 表 → 全量导出会报错，只导存在的表。
- `local_cache_reader.py`：`load_influencers()` / `video_map_by_channel()` 秒级读取。

### ⑦ 补算专用脚本 refresh_promo_lark.py
- 为什么存在：`main.py refresh --fields promo` 走应用身份鉴权报 `10014 app unauthorized`。
- 改走 YouTube API 抓描述 + lark-cli 用户身份写回；断点续传 + 硬编码 Clash HTTP 代理。

---

## 3. 主库现状（2026-09-04 实测）

| 指标 | 值 |
|---|---|
| 主表（网红详情表）总行数 | **1821**（唯一 Channel ID 1821，重复 0） |
| 匹配产品分布 | WEMOH C1 婴儿车载摄像头 **1129** / 足球护膝 **352** / AirTag 护照包(CFC1) **340** / 空 0 |
| 来源关键词 | 56 个关键词全覆盖，空来源 = 0 |
| 红人表 | 1821 行，与主表 Channel ID 完全一致 |
| 人工数据 | 已联系 103 条 / 备注 42 条 / 联系邮箱 604 条 |

VyH0 Base 现有 **6 张表**（映射见第 4 节）。CFC1 是独立 Base（<FEISHU_BASE_TOKEN_CFC1>，340 条），
可同步进主库（vyh0_sync_cfc1.py）。

---

## 4. 关键资产 & 配置

### 飞书 Base
- Base ID：`<FEISHU_BASE_TOKEN>`
- 链接：https://pcn8zy4grswl.feishu.cn/base/<FEISHU_BASE_TOKEN>
- 认证：`write_user_base.py` 里 `BASE_TOKEN` 已指向 VyH0。走 lark-cli `--as user` 用户身份。

### 飞书表 ID 映射（VyH0，6 张表）
| 表 | table_id | 记录数 | 备注 |
|---|---|---|---|
| 网红详情表 | `tbl4rnFUM9jJXvCQ` | 1821 | 主库核心全量表 |
| 视频数据表 | `tblDQi8dEGhkjZyy` | 5258 | 含 `描述` 字段 |
| 网红视频表 | `tblcHBORC90WWn05` | 5984 | 每频道 N 条（曾 22129 行超限，放本地） |
| 搜索任务表 | `tblLT1yf9ioEhJOh` | 29 | 每次搜索 1 行 |
| 红人表（派生） | `tblPKFENcpk8xnZH` | 1821 | 25 字段精简，增量同步，table_id 固定 |
| 红人表 maa 全表匹配 | `tblyy7XAfBhFdw5y` | — | 8 月全表匹配结果副本 |

> 足球评分表 `tble06acWNOPB6vX` 已删除（数据并入网红详情表评分列），export_local_cache.py 里残留引用需清理。

### 关键文件
| 文件 | 用途 |
|---|---|
| `main.py` | 搜索 / 合并 / sync-workbook 入口（--skip-hongren） |
| `write_user_base.py` | 清空+重写飞书（大版本替换） |
| `sync_hongren_table.py` | 红人表增量同步（不删表、保护人工列、--dedupe） |
| `score_influencers.py` | 离线评分写回 6 列（含 run_long + 断点续传 + list_all 读取器） |
| `rescore_soccer.py` | 定向重算足球护膝 |
| `refresh_promo_lark.py` | 补算 promo+邮箱（绕开坏掉的应用鉴权） |
| `clean_main_dupes.py` | 主表重复 Channel ID 清理（先备份） |
| `restore_nosource.py` | 无来源记录按 batch 反查补回 |
| `match_full_table.py` / `push_match_to_feishu.py` | 整表匹配评分 + 写回飞书 |
| `vyh0_sync_cfc1.py` / `vyh0_rescore_cfc1.py` | CFC1 独立 Base → 主库同步/重算 |
| `export_local_cache.py` | 一键导出飞书到本地 JSON |
| `local_cache_reader.py` | 本地缓存秒级读取器 |
| `product_profiles.json` | 产品画像配置（active = baby_car_camera_us，6 画像） |
| `filter/promo_detector.py` | 亚马逊推广分级 |
| `filter/email_extractor.py` | 多源邮箱提取 |
| `filter/scoring.py` | 内容契合 + 商务优先级评分 |

### 网络（YouTube API 必看）
- YouTube Data API 需翻墙。**代理 = Clash HTTP `http://127.0.0.1:7890`**（或读 HTTPS_PROXY 环境变量）。
  **`socks5h://127.0.0.1:10808` 已废弃（端口未开放），不要再用**。
- sandbox 后台 Bash 不继承命令行 `HTTPS_PROXY=...` 前缀；环境里的 HTTP_PROXY 是 WorkBuddy
  内网代理（不能翻墙）。跑 YouTube 脚本要显式设代理环境变量或传 `proxies` 参数。
- 跑这类脚本必须 `dangerouslyDisableSandbox: true` + `run_in_background: true`（前台会被 SIGKILL），
  且注意后台约 20 分钟回收上限（脚本需断点续传）。

### lark-cli
- **真实路径**：`/Users/coscod/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli`
  （write_user_base.py 顶部常量仍指向失效的 node/22.22.2 目录，**写脚本时需运行时覆盖 wb.LARK**）。
- **授权**：user token 失效后，`auth login --domain base --no-wait --json` 取 device_code →
  用户扫码 → **必须** `auth login --device-code <code> --json` 完成捕获（仅 --no-wait 会丢 token）。
- 子命令带 `+` 前缀（`+record-list` / `+field-list` / `+table-list` / `+record-batch-create` 等）；
  `record-delete` 需 `--yes`；`record-batch-update` 用 `{"update_records":{recId:{...}}}`，每批≤200。

---

## 5. 怎么跑（常用命令）

```bash
cd "/Users/coscod/WorkBuddy/coscod/YouTube 网红开发工作流系统/assets/yt-kol-workflow"

# —— 补算 promo + 邮箱（走 YouTube API，需翻墙，必须后台运行）——
./.venv/bin/python refresh_promo_lark.py              # 全量（跳过已处理的）
./.venv/bin/python refresh_promo_lark.py --limit=5    # 只跑 5 个（测试用）
./.venv/bin/python refresh_promo_lark.py --dry-run     # 只看不写

# —— 补算评分（只读飞书，不耗 YouTube 配额）——
./.venv/bin/python score_influencers.py --dry-run     # 预览
./.venv/bin/python score_influencers.py               # 写回（含断点续传）

# —— 红人表增量同步（源表改了想刷新时；幂等可重跑）——
./.venv/bin/python sync_hongren_table.py --dry-run    # 预览计划
./.venv/bin/python sync_hongren_table.py              # 执行同步
./.venv/bin/python sync_hongren_table.py --dedupe     # 额外清理重复 Channel ID

# —— 刷新本地缓存（写飞书后必跑；需 stub dotenv，见 SKILL.md 2.7）——
./.venv/bin/python export_local_cache.py influencers  # 单表（推荐）
# ./.venv/bin/python export_local_cache.py            # 全量（会撞已删 soccer 表，慎用）

# —— 跑新搜索 ——
python main.py batch --keywords-file keywords.txt -o output/<时间戳>_batch
python main.py merge-output output/<时间戳>_batch -o output/summary/kol_summary_tables.xlsx
python main.py sync-workbook --workbook output/summary/kol_summary_tables.xlsx \
    --feishu-app-token <FEISHU_BASE_TOKEN>

# —— 本地缓存读取示例 ——
./.venv/bin/python -c "
from local_cache_reader import load_influencers, video_map_by_channel
details = load_influencers()        # 1821 条，秒级
vmap = video_map_by_channel()       # {channel_id: [video_dict, ...]}
"
```

**重要**：跑评分前先确认 `product_profiles.json` 的 `active` 设成与该批搜索匹配的产品画像；
或显式传 profile 给 `score_influencer()`（传入 profile 优先级高于 active）。

---

## 6. 已知坑 / 必避陷阱（新对话直接继承；详见 skill SKILL.md 第 4 节）

### 环境 / lark-cli / 授权
1. **lark-cli 真实路径**：`cli-connector-packages/bin/lark-cli`；write_user_base.py 常量失效 → 运行时 `wb.LARK = <真实路径>`。
2. **授权流程**：`auth login --domain base --no-wait` 后**必须** `--device-code <code>` 捕获，否则 token 丢失。
3. **子命令带 `+` 前缀**；`record-delete` 需 `--yes`。
4. **`record-batch-update`**：`--json '{"update_records":{"recA":{"字段":值}}}'`，每批≤200。
5. **`record-batch-create`**：矩阵格式 `{"fields":[...], "rows":[...]}`；select 空值传 None 不能传 `''`。
6. **`record-list` 返回**：`data.fields`(列名) / `data.data`(行) / `data.record_id_list`(ID) 按索引对齐；无 total，全量要循环。
7. **`+field-list`**：字段名在 `data.fields[].name`（不是 field_name）。
8. **select 选项缺失报 not_found**：`+field-update` PUT 全量选项；`国家/地区` 用名字更新 404，用字段 ID `flddXjEdHW`；单选选项加色用 hue + lightness(Standard/Lighter)。
9. **`main.py refresh --fields promo` 写不进飞书**（应用身份 10014）→ 用 refresh_promo_lark.py。
10. **`ensure_schema` 给 field-create 传 `--yes` → 字段静默创建失败** → refresh_promo_lark/score_influencers 各自内置不带 --yes 的建字段逻辑。
11. **lark-cli `--json` 不支持绝对路径**：`@./相对名.json`。
12. **清空是最终一致**：循环列举→删除直到连续两次读到 0。
13. **select 值以 list 返回**（`['US']`）：统计前 `_str()`/`norm()` 展平。
14. **数字 int/float 假差异**：比较前统一 `f"{float(v):.6g}"`。
15. **`export_local_cache.py` 顶层 import dotenv（venv 未装）**：stub 或 pip install；EXTRA_TABLES 残留已删 soccer 表，全量导出会报错。
16. **sandbox 阻断 os.remove** → 覆盖不删；设 `LARK_CLI_NO_PROXY_WARN=1` 抑制警告。
17. **present_files 会把 .csv 转成 xlsx(zip)** → 别对要程序读取的 .csv 调 present_files。
18. **还原/清洗脚本关键词白名单须与实际批次同步**：曾漏 8/26 英文词把 273 条误清成"无来源"。

### YouTube API / 代理
19. **YouTube API 拿不到邮箱**（关于页验证码）→ 只能从视频描述抽。
20. **代理 = Clash HTTP `http://127.0.0.1:7890`**（socks5h 10808 已废弃）；显式设环境变量或 proxies 参数。
21. **带网络后台脚本前台跑被 SIGKILL** → `run_in_background: true` + `dangerouslyDisableSandbox: true`。
22. **后台约 20 分钟回收上限** → 长任务支持断点续传，重跑接上。

---

## 7. 第二次填关键词时，第一次的数据会怎样？

**关键在 `output_dir` 和合并时传了哪些 `batch_dir`。**

| 你怎么做 | 首轮数据在 Base 里的结果 |
|---|---|
| 把首轮+二轮所有关键词放进同一次 `batch` | 首轮数据全保留（一次合并去重）；但首轮关键词被重新搜索一遍，白费配额（search.list 约 100/词） |
| 二轮用新 output_dir，且 merge-output 只传二轮目录 + write_user_base 清空重灌 | 首轮从 Base 消失（文件仍在磁盘旧目录，只是没被合并） |
| 二轮用新 output_dir，但 merge-output 旧+新目录都传 | 首轮+二轮合并，去重后全保留 |
| 走 sync-workbook（增量 upsert） | 只增改不删，主库已有记录保留 |
| 二轮复用同一 output_dir | 首轮可能被覆盖（除非关键词含首轮） |

**推荐**：关键词只搜一次，跨轮累计靠 `merge-output` 目录合并（按 Channel ID 去重）。
日常维护走增量 upsert 脚本，避免无谓的清空重灌。

---

## 8. 待办 / 需要新对话确认的事项

1. **足球护膝评分质量**（2026-09-04）：352 条里 131 条 0 分（37.2%）、均值 10.4、优先级 C 311/B 37/A 4。
   原因是画像关键词偏产品词（shin guards）而足球频道内容多泛足球。可选方向：
   市场放宽到 UK/CA/AU、下调 min_views/互动阈值、补泛足球关键词（soccer/football/youth soccer/skills）。
   调完用 `rescore_soccer.py` 重跑即可（幂等，不覆盖人工列）。
2. **评分口径调优**：C 档占比过高，可能需要调 `product_profiles.json` 门槛或 `scoring.py` 权重。
3. **export_local_cache.py 清理**：EXTRA_TABLES 删掉已删除的 soccer_scores 残留（tble06acWNOPB6vX），
   或保持"只导存在的表"习惯。
4. **主表 649 条"匹配产品为空"的旧说法已过时**：现在是 0 空（足球 352 已补算、297 重复已删）。
5. 未来跑新产品线搜索时：切 product_profiles active → 搜索 → sync-workbook → refresh_promo → 评分 → 刷缓存。

---

## 9. 业务背景速览

- **品牌**：Stouchi（Apple 生态配件 / 旅行配件，Amazon 美店 Stouchi-US，Mac mini M4 扩展坞 ASIN B0GJ54TC4V、
  AirTag 护照包 ASIN B0G1BTYYX6）、WEMOH（母婴科技，婴儿车载摄像头 ASIN B0F6N9PHHW，Amazon US + DE）、
  AirsFish（儿童/青少年护具：护腿板 B0FJBRQ6V5、护膝 B0B5XTW9T4/B0BWF4LT75）。
- **岗位**：用户一人负责亚马逊「站外推广」岗（PB 联盟客 CPS + 红人两条线）。独立站另有市场部。
- **用户评估红人匹配度的真实口径**：① 粉丝数只分 KOL/KOC 层级，本身不加权 ② 互动率判断粉丝质量
  ③ 最大加分项：做过相关产品（高播放+有互动） ④ 亚马逊推广经验 = 加分 + 商务优势（好沟通、报价固定）。
- **当前数据**：主库 1821 红人（WEMOH 1129 + 足球 352 + CFC1 340），promo/邮箱/评分已全量。
- **PB 平台机制**：联盟营销 2 个月结算一次，默认佣金 20%、单品可调高（如护照夹 30%），纯链接推广。

---

## 10. 给新对话的一句话接力建议

存量数据（1821 红人）的 promo/邮箱/评分已全部跑完、两表一致、无重复无空值。
下一步大概率是：① 调足球画像后重跑评分（rescore_soccer.py）降 C 档；② 或跑新产品线新搜索
（切 active → 搜索 → sync-workbook → refresh_promo → score → 刷缓存）。
动手前读一遍 skill `yt-kol-feishu-sync/SKILL.md` 第 4 节「踩坑清单」，尤其坑 1/2/9/20/21。
