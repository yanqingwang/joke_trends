# joke_trends — 每周热点趋势报告（自动生成）

每周一早上（北京时间 11:00 左右）由 GitHub Actions 自动抓取全网公开数据源，生成一份「群众的快乐与焦虑」周报，Markdown 形式，内含内联 SVG 图表，直接可分享。

## 报告内容

| 板块 | 数据源 |
|---|---|
| GitHub Star 火箭榜 | GitHub REST（关注盘 + 30 天新冒头 AI 仓库） |
| 预测市场风向 | Polymarket Gamma API |
| AI 模型动态 | HuggingFace 热度榜（可选配 AA_API_KEY 拿智能指数） |
| 热搜雷达 | 今日头条 / 百度 top / X（getdaytrends、trends24）/ Google Trends RSS |
| 加密货币情绪 | alternative.me 恐惧贪婪指数 + CoinGecko/Yahoo + 爆仓新闻 RSS |
| 黄金/美元/宏观 | gold-api.com + Yahoo Finance + 欧央行汇率 |
| 全球贸易风向 | ECB 汇率篮子 + CNBC/Google News RSS |
| SaaS 签单 / AI 融资 / AI 落地 | TechCrunch / VentureBeat / Crunchbase / Product Hunt RSS + HN Algolia |
| Linux / 开源动态 | Phoronix / LWN / DistroWatch RSS |
| 电脑硬件 & 内存行情 | Tom's Hardware / TechPowerUp RSS（DDR5/内存/SSD/GPU 关键词） |
| 前沿科学雷达 | arXiv 最新提交（cs.AI / cs.CL / cs.LG / quant-ph） |
| 科技招聘前沿 | HN Who-is-hiring + Greenhouse / Lever 公共岗位 API |

每节条数受限（默认 ≤5 条），保证「扫一眼能看完」。

## 本地运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --profile joke
```

输出：`reports/{year}-W{ww}.md`（`reports/weekly.md` 固定为最新一期）。

## 架构说明

- `sources.yml`：所有数据源的配置（开关、关键词、列表）都集中在这里，改这里就能改报告。
- `src/sources/*.py`：一个数据源一个文件，统一返回 `{ok, bullets, chart, extra, note, state}`。
- `src/main.py`：编排所有源，**任何一根管道挂掉都不会让整份报告崩**——只会标红降级并回退上周缓存数据（`data/state-{profile}.json` 存上期状态用于算周环比）。
- `src/render.py` + `src/svgchart.py`：渲染 Markdown + 纯手写内联 SVG 图表，零图片依赖。

## 手动补充

每周需要人工编辑的地方：

- `manual/notes.md` —— 全局补充，会进「✍️ 手动补充区」。

## 可选增强

- 设置 GitHub Secret `AA_API_KEY`（artificialanalysis.ai 免费 key）→ AI 评测指数板块自动点亮。
- 部分数据源（Polymarket / Google Trends）在部分网络环境下被区域屏蔽，本仓库跑在 GitHub Actions 美国机房，通常可达；不可达时报告会明示降级而不是静默消失。
