# 今天吃什么 · 校园决策助手

课程《软件工程》小组项目：一个面向本校两个校区（马房山、南湖）的**吃饭决策助手**。网页界面 + Python（Flask）后端 + SQLite。输入校区、时段、预算和口味，转盘 / 抽签决定吃什么；支持评分评论、群体投票聚餐地点、后台维护菜品与数据看板。

> **仓库状态（2026-11-14）**：这是**项目规划设计 + 可运行脚手架**。参考实现完整可跑（`python run.py`），正式实现留了 `raise NotImplementedError  # TODO` 给各负责人按分工完成；文档 01–07、契约测试、进度看板、调研模板都已就位。编译/运行见下文。

## 快速开始

> 需要 Python 3.10+。如果机器上 `python` 是 2.x（本机 Miniconda 就是），把下面命令里的 `python` 换成 `py -3` 即可。

```bash
python -m venv .venv
.venv\Scripts\activate             # Windows；macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

python run.py --open               # http://127.0.0.1:3200，自动打开首页
python run.py --lan                # 手机同 Wi-Fi 可打开投票链接
pytest                             # 跑测试，最后打印每个人的进度
```

Windows 也可以直接双击 `start.bat`。

最终演示用全部正式实现：

```bash
python run.py --real all --open
```

### 常用参数

```bash
python run.py --real catalog,stats   # 只把某些组件换成正式实现
python run.py --real decision        # 只换决策 / 投票
python run.py --db data/demo.db      # 指定 SQLite 文件
python run.py --port 3300            # 换端口
```

组件名：`repository`、`catalog`、`reviews`、`decision`、`vote`、`stats`。没写完的组件自动用参考实现顶上，**谁都不用等别人**。

## 功能

- **抽签 / 转盘**：按校区、时段、预算、分类、口味筛选；排除“不吃辣”、最近 7 天吃过的、指定不想要的菜；按评分与近 30 天热度加权随机，返回 2 个备选。
- **评分与评论**：1–5 星、昵称、200 字评论；同一人同一道菜每天一条；平均分与分布进入抽签权重。
- **群体投票**：6 位分享码，2–8 个候选地点，一人一票、可改票、到点自动截止；平票明确提示。
- **管理后台**：菜品 / 窗口新增与修改、上下架、评价管理、数据看板（抽签次数、评价、评分、投票参与、热门菜 Top 5）。
- **多校区 + 真实调研**：马房山、南湖；演示数据标注 `DEMO`，调研数据按 07 号文档导入。

## 五个人怎么分工

| 角色 | 成员代号 | 负责代码 |
|---|---|---|
| A 项目 / 产品 + UI & 文档 | A | `web/api.py`、`admin.html`、`admin.js`、`theme.css`、`docs/` |
| B 技术负责人（兼后端） | B | `decision/**`、`wiring.py`、集成 |
| C 后端开发 | C | `model/**`、`catalog/**`、`schema.sql` |
| D 前端开发 | D | `index.html`、`vote.html`、`app.js`、`vote.js`、`api.js`、`app.css` |
| E 测试 / 运维（兼评价） | E | `review/**`、`tests/**`、`tools/import_survey.py`、启动与环境 |

组内只使用 A–E 代号，仓库与文档不记录姓名；代号是建议分配，可在组内互换。**角色职责、代码边界、工时与里程碑见 [06 分工与里程碑](docs/06-分工与里程碑.md)**。课程要求全体成员都承担开发任务，所以每个人都有明确的代码与测试产出。

## 怎么开工

1. 读 `docs/01-需求规格.md` 和 `docs/06-分工与里程碑.md` 里你的部分；
2. 打开你负责的文件，把 `raise NotImplementedError  # TODO` 换成实现；
3. 跑 `pytest -k "real and <你的模块>"`，直到全绿；
4. `python run.py --real <你的组件>` 在完整程序里看效果；
5. 合并前跑 `pytest -k reference`，保证没把别人的测试改坏。

## 文档

| 文档 | 内容 |
|---|---|
| [01 需求规格](docs/01-需求规格.md) | 按角色拆的需求（必做 / 加分）、非功能需求、假设、演示脚本 |
| [02 系统架构](docs/02-系统架构.md) | 技术选型、分层、依赖规则、参考 / 正式实现、目录结构 |
| [03 详细设计](docs/03-详细设计.md) | 数据模型、筛选管线、权重公式、投票状态机、评价规则、统计口径 |
| [04 接口契约](docs/04-接口契约.md) | Python 接口、HTTP 接口、JSON 示例、改接口流程 |
| [05 测试计划](docs/05-测试计划.md) | 测试分层、需求 ↔ 测试对照、界面验收清单、缺陷跟踪 |
| [06 分工与里程碑](docs/06-分工与里程碑.md) | 5 人角色映射、每人任务、依赖、活动 1–6 时间线、风险 |
| [07 调研与数据采集](docs/07-调研与数据采集.md) | 两校区调研计划、CSV 字段、导入流程、合规与隐私 |

## 仓库结构

```
campus-eats/
├─ run.py / start.bat / requirements*.txt / pytest.ini
├─ docs/                      01–07
├─ surveys/survey-template.csv
├─ tools/import_survey.py
├─ campus_eats/
│  ├─ model/                  实体、枚举、错误、Clock、Repository、初始数据
│  ├─ catalog/                CatalogService、StatsService（C）
│  ├─ review/                 ReviewService（E）
│  ├─ decision/               DecisionService、VoteService（B）
│  ├─ web/                    api.py + static/（A / D）
│  ├─ testing/reference.py    参考实现（内存版）
│  └─ wiring.py               组装
├─ tests/
│  ├─ contract/               契约测试（每个服务 reference / real 各跑一遍）
│  ├─ api/                    HTTP 接口测试
│  ├─ integration/            全流程集成测试
│  ├─ conftest.py             夹具 + 进度看板
│  └─ helpers.py
└─ data/                      SQLite（.gitignore）
```

## 测试进度

参考实现必须全绿；正式实现按模块逐个变绿：

```bash
pytest -k reference    # 提交前必须全绿
pytest                 # 看所有人的进度表
pytest -k real         # 只看正式实现
```

> 当前仓库的正式实现还是 `NotImplementedError`，所以直接跑 `pytest` 会看到大量“未实现”（这是脚手架的设计）；`pytest -k reference` 应该全绿。

界面验收清单在 05 号文档 §5；调研数据导入检查在 §6。

## Git 协作

- 每人一个分支：`feat/web-a`、`feat/decision-b`、`feat/data-c`、`feat/frontend-d`、`feat/qa-e`；
- 合并到 `main` 前：`pytest -k reference` 全绿 + 至少 1 人 review；
- 改接口：走 `docs/04-接口契约.md` §4 的流程；
- 不提交 `data/`、`*.db`、含个人信息的调研原始材料；仓库只放脱敏 CSV 与模板。

## 数据说明

仓库里的食堂、窗口、菜品、评价都是**演示数据**（`source=DEMO` / `TAKEOUT`），不代表学校真实菜单。真实数据按 07 号文档线下调研后导入，并在页面显示来源。不爬取任何外卖平台；外卖只做手工录入样例。
