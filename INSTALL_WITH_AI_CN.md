# 用 AI 助手安装和使用本工作流（中文教程）

> 本文档教你如何通过 AI 编程助手（WorkBuddy、Codex CLI、Cursor、Windsurf 等）零门槛安装和运行 YouTube KOL 开发工作流。
>
> 不需要记命令、不需要懂 Python——只需要在 AI 对话框里粘贴提示词即可。

---

## 目录

1. [兼容的 AI 平台](#1-兼容的-ai-平台)
2. [前置条件](#2-前置条件)
3. [安装（复制提示词给 AI）](#3-安装复制提示词给-ai)
4. [配置 YouTube API Key](#4-配置-youtube-api-key)
5. [准备关键词并启动搜索](#5-准备关键词并启动搜索)
6. [合并搜索结果](#6-合并搜索结果)
7. [同步到飞书多维表格](#7-同步到飞书多维表格)
8. [补算亚马逊推广经验 + 邮箱](#8-补算亚马逊推广经验--邮箱)
9. [产品匹配度评分](#9-产品匹配度评分)
10. [构建红人表 + 本地缓存](#10-构建红人表--本地缓存)
11. [AI 提示词速查表](#11-ai-提示词速查表)
12. [常见问题](#12-常见问题)

---

## 1. 兼容的 AI 平台

以下平台均可使用本工作流，只要支持「读写本地文件 + 执行终端命令」即可：

| 平台 | 支持情况 | 备注 |
|------|----------|------|
| **WorkBuddy** | 完整支持 | 可直接加载 SKILL.md，AI 自动理解全流程 |
| **Codex CLI (OpenAI)** | 完整支持 | 读取 SKILL.md 后可执行全部命令 |
| **Cursor** | 完整支持 | 在 Composer/Chat 中粘贴提示词即可 |
| **Windsurf** | 完整支持 | Cascade 模式中粘贴提示词即可 |
| **GitHub Copilot Chat** | 部分支持 | 需手动在终端执行命令，AI 辅助生成 |
| **其他支持文件操作的 AI** | 应该可用 | 只要能读写文件、跑命令就行 |

> **推荐 WorkBuddy**：本项目自带 `SKILL.md`，WorkBuddy 会自动加载并理解全部工作流细节，无需手动粘贴。

---

## 2. 前置条件

在使用 AI 安装前，请确认你的电脑已经具备以下条件：

### 必需

- **Python 3.9+**：在终端运行 `python3 --version` 确认
- **YouTube Data API v3 密钥**：用 Gmail 在 [Google Cloud Console](https://console.cloud.google.com/) 免费申请
  - 启用 "YouTube Data API v3"
  - 创建 API Key（免费配额：每日 10,000 units）

### 可选（飞书同步才需要）

- **Node.js + npx**：飞书 CLI（lark-cli）依赖
- **飞书账号**：用于浏览器 OAuth 授权
- **网络代理**：如果你的地区无法直接访问 YouTube API，需配置 HTTP 代理

### 不需要

- 不需要懂 Python 编程
- 不需要手动装依赖（AI 会帮你装）
- 不需要记命令行参数（AI 会帮你拼）

---

## 3. 安装（复制提示词给 AI）

### 方式 A：从 GitHub 克隆安装

把以下提示词复制粘贴到你的 AI 助手对话框：

```
请帮我从 GitHub 克隆 YouTube KOL 工作流项目并完成初始化：

1. 克隆仓库：git clone https://github.com/yourusername/yt-kol-workflow.git
2. 进入项目目录：cd yt-kol-workflow/assets/yt-kol-workflow
3. 创建 Python 虚拟环境：python3 -m venv .venv
4. 激活虚拟环境：source .venv/bin/activate
5. 安装依赖：pip install -r requirements.txt
6. 从示例创建配置文件：
   - cp .env.example .env
   - cp keywords.example.txt keyword.txt
   - cp brand_exclusions.example.json brand_exclusions.json
7. 安装完成后告诉我下一步该做什么
```

> **Windows 用户**：第 4 步改为 `.venv\Scripts\activate`

AI 会自动执行以上所有步骤，完成后告诉你结果。

### 方式 B：用项目自带的初始化脚本

如果你的 AI 在项目根目录，可以用：

```
请运行项目自带的初始化脚本：
python scripts/bootstrap_workflow.py --target ./yt-kol-workflow --install-deps

完成后告诉我安装结果和下一步操作。
```

### 方式 C：已有项目目录

如果你已经把项目文件放在了某个目录，只需：

```
我已经把 yt-kol-workflow 项目放在了 /path/to/yt-kol-workflow/assets/yt-kol-workflow 目录。
请帮我：
1. 在该目录创建 .venv 虚拟环境并安装 requirements.txt
2. 从 .env.example 创建 .env
3. 从 keywords.example.txt 创建 keyword.txt
```

---

## 4. 配置 YouTube API Key

安装完成后，AI 会提示你配置 API Key。把以下提示词给 AI：

```
请帮我编辑 .env 文件，将 YOUTUBE_API_KEY 的值设置为：AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

（请把上面这串替换成你真实的 API Key）

同时检查 .env 文件中是否有以下可选配置需要填写：
- HTTPS_PROXY（如果需要代理访问 YouTube API）
- FEISHU_AUTH_MODE（飞书认证模式，默认 auto 即可）
```

### 如何获取 YouTube API Key

如果你不知道怎么申请，可以直接问 AI：

```
我不太清楚怎么申请 YouTube Data API v3 的 API Key，请帮我详细说明步骤。
```

AI 会给你完整的图文指引。

### 配置代理（如果需要）

如果你的网络无法直接访问 YouTube API：

```
请帮我在 .env 文件中设置代理：
- HTTPS_PROXY=http://127.0.0.1:7890
- HTTP_PROXY=http://127.0.0.1:7890

（请把端口改成你实际使用的代理端口）
```

---

## 5. 准备关键词并启动搜索

### 创建关键词文件

把以下提示词给 AI，让它帮你创建关键词文件：

```
请帮我在项目目录创建 keyword.txt 文件，每行一个关键词，内容如下：

baby monitor
baby car camera
rear facing car seat
newborn essentials
parenting products

保存完成后，运行以下命令启动批量搜索：
source .venv/bin/activate
python main.py batch --keywords-file keyword.txt -o output/my_first_batch --sort-order relevance --yes --no-feishu
```

> - `--no-feishu`：先只生成本地 Excel，不同步飞书（第一轮推荐这样做）
> - `--sort-order relevance`：按相关度排序，质量更高
> - `--yes`：跳过交互确认
> - `-o output/my_first_batch`：指定输出目录

### 搜索需要多久

- 每个关键词约消耗 100 API 配额（search.list）
- 10 个关键词 ≈ 5-10 分钟
- 17 个关键词 ≈ 15-30 分钟
- 如果 AI 在后台运行长任务，你可以去做别的事，完成后会通知你

### 搜索完成后

AI 会告诉你输出文件的位置：

```
output/my_first_batch/
├── search_tasks_all.xlsx       # 搜索任务汇总
├── search_videos_all.xlsx      # 视频数据
├── influencers_all.xlsx        # 网红详情
└── influencer_videos_all.xlsx  # 网红视频
```

---

## 6. 合并搜索结果

如果你跑了多轮搜索（比如先搜英文关键词，再搜德语关键词），需要把多个批次合并：

```
请帮我把多个搜索批次合并成一个汇总表：

python main.py merge-output output/第一批次 output/第二批次 -o output/summary/kol_summary_tables.xlsx

合并时按 Channel ID 去重，同一网红不会重复出现。
```

> **重要**：`merge-output` 的批次目录是位置参数（直接跟在命令后面），不是 `--batch-dirs`。

如果只有一轮搜索：

```
请帮我合并这一轮的搜索结果：
python main.py merge-output output/my_first_batch -o output/summary/kol_summary_tables.xlsx
```

---

## 7. 同步到飞书多维表格

### 首次设置（创建飞书 Base）

```
请帮我运行飞书初始化：
python main.py feishu-setup

这个命令会：
1. 检测或安装 lark-cli
2. 打开浏览器进行飞书 OAuth 授权
3. 创建一个新的多维表格（Base）
4. 创建 4 张标准数据表

我需要在浏览器中做什么操作吗？
```

### 首次同步数据

首次建好 Base 后：

```
请帮我执行首次数据同步：
python sync_to_user_base.py

这会创建 Base + 4 张表并写入全部数据。只跑这一次。
```

### 后续同步（清空 + 重写）

以后每次搜索新关键词并合并后：

```
请帮我同步更新后的数据到飞书：
python write_user_base.py

注意：这会清空 4 张表并重新写入。字段配置和视图会保留，但逐行手填的值会被覆盖。
```

> **注意事项**：
> - `write_user_base.py` 是"清空重写"模式——你在飞书界面里逐行标注的值（如"已联系"）下次同步会丢失
> - 字段配置（加字段、改类型）和视图（筛选、分组）始终保留
> - 如果要保留手动标注，需要改为 upsert 模式（高级用法，咨询 AI）

---

## 8. 补算亚马逊推广经验 + 邮箱

搜索完成后，可以自动检测每个网红的亚马逊推广经验和联系方式：

```
请帮我运行推广经验和邮箱补算：
source .venv/bin/activate
python refresh_promo_lark.py

这个脚本会：
1. 逐频道拉取最近 25 条视频描述（走 YouTube API）
2. 自动分级亚马逊推广经验（6 级分类）
3. 多源抽取商务邮箱（按跨视频出现频次排序）
4. 结果写回飞书网红详情表
5. 已有邮箱的行不会被覆盖
6. 支持断点续传，重跑只补未处理的

预计耗时：500 个频道约 30 分钟，建议后台运行。
```

### 推广经验分级说明

| 级别 | 含义 | 价值 |
|------|------|------|
| Amazon Storefront | 已加入 Amazon Influencer Program | 最高 |
| Amazon 联盟客 | Amazon 链接带 ?tag= 联盟 ID | 高 |
| 挂过 Amazon 链接 | 有 amzn.to/a.co/amazon 链接 | 中 |
| 其他联盟带货 | geni.us/LTK/ShopMy 等 | 中 |
| 接过赞助 | #ad/paid promotion | 中 |
| 未发现 | 没有检测到推广痕迹 | 低 |

---

## 9. 产品匹配度评分

根据你的产品画像，给每个网红打 S/A/B/C 优先级评分：

### 第一步：配置产品画像

```
请帮我编辑 product_profiles.json，新增一个产品画像：

{
  "active": "my_product_name",
  "profiles": {
    "my_product_name": {
      "name": "我的产品名称",
      "keywords": ["关键词1", "关键词2", "关键词3"],
      "content_types": ["评测", "开箱", "使用体验"],
      "markets": ["US"],
      "min_views": 10000,
      "min_engagement": 2.0
    }
  }
}

确保 active 指向新添加的画像名称。
```

### 第二步：运行评分

```
请帮我运行产品匹配度评分：
python score_influencers.py

评分逻辑：
- 视频标题/Tags/描述匹配产品关键词 → 内容契合度 0-100 分
- 亚马逊推广经验 + 邮箱 + 互动率 + 更新频率 → S/A/B/C 优先级
- 结果写回飞书 6 列：匹配产品 / 品牌匹配度 / 内容契合类型 / 匹配关键词 / 开发优先级 / 推荐理由
- 不消耗 YouTube API 配额，只读飞书数据
- 支持断点续传

可以先 --dry-run 预览：
python score_influencers.py --dry-run
```

### 评分等级

| 等级 | 含义 |
|------|------|
| **S** | 完美匹配 + 有 Amazon Storefront/联盟 + 有邮箱 + 活跃更新 |
| **A** | 良好匹配 + 有亚马逊推广经验 + 有邮箱 |
| **B** | 部分匹配，或有推广经验/邮箱但不同时具备 |
| **C** | 相关度低，无推广经验，无邮箱 |

---

## 10. 构建红人表 + 本地缓存

### 构建精简红人表

```
请帮我运行红人表构建脚本：
python build_hongren_table.py

这会从网红详情表派生一个 25 列的精简表，包含 promo/邮箱/评分列。
每次重建会删旧表再建（table_id 会变），脚本自动处理。
```

### 导出本地缓存

```
请帮我导出本地缓存：
python export_local_cache.py

这会把飞书 4 张表的全量数据导出为本地 JSON 文件，方便后续秒级读取分析。
缓存目录：local_cache/
  - influencers.json    （网红详情表）
  - videos.json         （视频数据表）
  - channel_videos.json （网红视频表）
  - search_tasks.json   （搜索任务表）
  - hongren.json        （红人表）

写飞书后必跑一次刷新本地缓存，否则后续脚本读到旧数据。
```

---

## 11. AI 提示词速查表

以下提示词可以直接复制粘贴给 AI 助手：

### 一句话全流程

```
请帮我用以下关键词搜索 YouTube 网红，搜索完成后合并、同步飞书、补算 promo 和邮箱、评分、建红人表、导出本地缓存：
关键词1、关键词2、关键词3

产品画像是：XXX（简要描述产品）
目标市场：US
搜索地区：US
语言：en
```

### 分步速查

| 你想做什么 | 复制给 AI 的提示词 |
|------------|-------------------|
| 安装项目 | `请克隆 yt-kol-workflow 并完成 venv + 依赖安装 + 配置文件创建` |
| 配置 API Key | `请帮我在 .env 中设置 YOUTUBE_API_KEY=你的Key` |
| 搜索网红 | `请用关键词文件 keyword.txt 跑批量搜索，输出到 output/新批次 目录` |
| 合并批次 | `请合并 output/批次A 和 output/批次B，输出到 output/summary/kol_summary_tables.xlsx` |
| 首次建飞书表 | `请运行 sync_to_user_base.py 创建飞书 Base 和 4 张表` |
| 同步飞书 | `请运行 write_user_base.py 同步数据到飞书` |
| 补算推广+邮箱 | `请运行 refresh_promo_lark.py 补算亚马逊推广经验和邮箱` |
| 评分 | `请运行 score_influencers.py 给网红打 S/A/B/C 评分` |
| 建红人表 | `请运行 build_hongren_table.py 构建精简红人表` |
| 导出缓存 | `请运行 export_local_cache.py 导出本地 JSON 缓存` |
| 只看不写 | `请在 score_influencers.py 后面加 --dry-run 先预览再写` |
| 配代理 | `请在 .env 设置 HTTPS_PROXY=http://127.0.0.1:7890` |

### 高级用法

| 场景 | 提示词 |
|------|--------|
| 只搜不存飞书 | `搜索时加 --no-feishu，只生成本地 Excel` |
| 改地区和语言 | `搜索时加 --region DE --lang de`（德国/德语） |
| 调筛选阈值 | `搜索时加 --min-views 5000 --min-engagement 2 --filter-mode and` |
| 只搜中等时长视频 | `搜索时加 --video-duration medium` |
| 只搜 2025 年后的视频 | `搜索时加 --published-after 2025-01-01` |
| 每词最多 50 条 | `搜索时加 --max-results 50` |
| 按播放量排序 | `搜索时加 --sort-order viewCount` |
| 给存量红人回填 | `运行 refresh_promo_lark.py，已有邮箱的行不会被覆盖，断点续传` |
| 测试只跑 5 个频道 | `运行 refresh_promo_lark.py --limit=5 先验证效果` |

---

## 12. 常见问题

### Q: AI 说"找不到 YouTube API Key"

告诉 AI：
```
请检查 .env 文件中 YOUTUBE_API_KEY 是否已正确填写，值以 AIza 开头。
如果文件不存在，请从 .env.example 复制一份再编辑。
```

### Q: 飞书同步提示权限不足

告诉 AI：
```
飞书同步报权限错误，请帮我重新授权：
lark-cli --profile kol-workflow auth login --scope 'bitable:app:readonly bitable:app base:record:retrieve'
授权完成后重试同步。
```

### Q: 搜索结果为空或很少

可能原因和解决方案：
```
请帮我检查：
1. 关键词是否太窄或太宽
2. 试试 --min-views 5000 --min-engagement 2（降低阈值）
3. 试试 --filter-mode or（默认，任一达标即可）
4. 换 --sort-order viewCount（按播放量排，可能有更多结果）
5. 确认 --region 和 --lang 是否匹配（如搜德语用 --region DE --lang de）
```

### Q: YouTube API 配额用完了

```
YouTube 每日免费配额 10000 units，每个关键词搜索消耗 100 units。
今天用完了只能等明天重置（太平洋时间午夜）。
可以在 Google Cloud Console 申请提高配额上限。
```

### Q: 网络不通 / API 超时

```
请帮我检查网络是否能访问 YouTube API：
curl -s "https://www.googleapis.com/youtube/v3/videos?part=snippet&id=test&key=YOUR_KEY" | head

如果超时，请在 .env 中设置代理：
HTTPS_PROXY=http://127.0.0.1:7890
```

### Q: 代理端口是多少

```
请帮我检测当前系统可用的代理端口：
- 检查 Clash: lsof -i :7890
- 检查 V2Ray: lsof -i :10808
- 检查环境变量: echo $HTTPS_PROXY
```

### Q: macOS 看不到 .env 文件

`.env` 是隐藏文件。在 Finder 中按 `Command + Shift + .` 显示隐藏文件。
或者直接让 AI 帮你编辑：
```
请帮我读取 .env 文件内容并修改 YOUTUBE_API_KEY 的值
```

### Q: write_user_base.py 清空了我的手动标注

这是已知行为。`write_user_base.py` 是"清空重写"模式。
```
请帮我了解：
- 字段配置和视图始终保留
- 逐行手填的值（如"已联系"状态）会被覆盖
- 如果要保留手动标注，需要改为 upsert 模式
- 替代方案：在飞书里单独建一个"手动跟进"表，用 Channel ID 关联
```

### Q: 第二轮搜索，第一轮数据会丢吗

```
关键看 merge-output 传了哪些目录：
- 只传第二轮目录 → 第一轮从飞书消失
- 旧+新目录都传 → 全部保留，按 Channel ID 去重
- 正确做法：关键词只搜一次，跨轮累计靠 merge-output 合并目录
```

### Q: 网红视频表太大同步不了

飞书单表有记录上限（约 20,000-50,000 行，视表配置而定）。
```
如果网红视频表超限：
1. 不同步该表到飞书，数据保留在本地 Excel / JSON
2. 用 export_local_cache.py 导出本地缓存
3. 用 local_cache_reader.py 秒级读取分析
```

### Q: 评分全是 C

```
请检查 product_profiles.json 的 active 是否指向正确的产品画像。
如果画像与搜索关键词不匹配，内容契合度会得地板分（10分），导致全 C。
确保画像中的 keywords 字段覆盖了搜索时用的关键词。
```

---

## 附录：完整工作流速查图

```
┌─────────────────────────────────────────────────────────────┐
│                      完整工作流速查                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: 配置                                                │
│  ┌──────────────────────────────────┐                       │
│  │ .env → YOUTUBE_API_KEY           │                       │
│  │ keyword.txt → 每行一个关键词       │                       │
│  │ product_profiles.json → 产品画像   │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 2: 搜索                                                │
│  ┌──────────────────────────────────┐                       │
│  │ python main.py batch              │                       │
│  │   --keywords-file keyword.txt     │                       │
│  │   -o output/batch_1               │                       │
│  │   --sort-order relevance --yes    │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 3: 合并                                                │
│  ┌──────────────────────────────────┐                       │
│  │ python main.py merge-output       │                       │
│  │   output/batch_1 [output/batch_2] │                       │
│  │   -o output/summary/kol.xlsx      │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 4: 同步飞书                                             │
│  ┌──────────────────────────────────┐                       │
│  │ 首次: python sync_to_user_base.py │                       │
│  │ 后续: python write_user_base.py   │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 5: 补算推广+邮箱                                        │
│  ┌──────────────────────────────────┐                       │
│  │ python refresh_promo_lark.py      │                       │
│  │ (需 YouTube API + 可能需代理)      │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 6: 评分                                                │
│  ┌──────────────────────────────────┐                       │
│  │ python score_influencers.py       │                       │
│  │ (只读飞书，不耗 YouTube 配额)       │                       │
│  └──────────────┬───────────────────┘                       │
│                 ↓                                           │
│  Step 7: 派生表 + 缓存                                        │
│  ┌──────────────────────────────────┐                       │
│  │ python build_hongren_table.py     │                       │
│  │ python export_local_cache.py      │                       │
│  └──────────────────────────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 下一步

- **达人外联**：评分完成后，按 S → A → B 优先级联系网红。可以让 AI 根据产品信息生成首次联系邮件模板（含三问：地址 / 是否收费 / 版权费用）。
- **定期刷新**：每周重跑 `refresh_promo_lark.py` 补充新频道的推广经验和邮箱。
- **扩展关键词**：发现新的产品相关关键词后，单独跑 `batch`，再 `merge-output` 合并旧目录。
- **多市场**：用不同 `--region` / `--lang` 搜索不同市场（如 `--region DE --lang de` 搜德国市场）。

---

> 有问题？直接把报错信息粘贴给 AI 助手，它会帮你诊断和修复。
