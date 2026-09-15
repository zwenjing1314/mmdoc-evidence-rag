# 工作交接记录（变化的进度）

> 用途：新开 Cursor 窗口时手动 `@docs/handoff.md`，让新会话接上当前进度。
> 约定：每次会话结束前更新本文件；`docs/handoff.md` 只写变化的进度，不写不变的规范（规范在 `.cursor/rules/`，自动生效）。

## 当前 Phase 与 Gate 状态

- 当前所处阶段：Phase 1A 已完成（EXP-002 正式登记）；下一步 Phase 1B 缺口诊断；项目整体处于"新项目搭建/脚手架启动"前夜。
- 已完成的 Phase：
  - Phase 0：uv 环境锁定、MMDocIR 数据准备、ViDoRe V1 官方复现（`docs/reproduction/colpali_vidore_v1_reproduction_20260830.md`，仅证明 checkpoint 可用）。
  - Phase 1A：ColPali full baseline（EXP-002）；BM25/Dense/Hybrid 对照 config 已备好但尚未跑全量。
- 下一个 Gate：

```text
Gate 通过条件：Phase 1B 产出 A/B/C/D 四类统计 + 按类型/面积/OCR密度分层 + 10成功/10失败可视化，且 B 类（页中区不中）稳定存在
下一步任务：新项目搭建——按小论文规范第 10 节搭 src/mmdocrag 脚手架（layout 节点编码、W 计算、region_metrics、坐标审计），然后做坐标审计
阻塞问题（如有）：坐标审计未做（W 计算的前置硬 Gate）；mmdocir_bm25/dense/hybrid 页级对照未跑全量
```

## 最近 runs

| EXP | run 目录（完整 timestamp） | 关键指标一句 | 是否可用 |
| --- | --- | --- | --- |
| EXP-001 | `runs/retrieval/mmdocir_colpali_smoke/20260912_123624` | smoke：6 query，Page R@5=1.0，流程验证 | 否（smoke 永不进论文） |
| EXP-002 | `runs/retrieval/mmdocir_colpali/20260912_221714` | Page R@1/5/10 = 0.5724/0.8390/0.9047，MRR=0.6890，nDCG@5/10 = 0.6932/0.7231，hits=30112 | 是（Phase 1A 正式 baseline，commit `fbf596f` 复评） |
| 历史无效 | `runs/retrieval/mmdocir_colpali/20260831_163643`、`20260831_163043` | 仅排错参考 | 否 |

## 配置与分支状态

- 当前分支：`thesis/structdocir`
- 未提交改动（`git status --short` 摘要）：
  - 修改：`README.md`、`docs/01-quickstart.md`、`docs/02-commands.md`、`pyproject.toml`、`uv.lock`、`src/mmdocrag/retrieval/colpali.py`、`tasks.ps1`
  - 新增未跟踪：`.cursor/`（4 条 rules）、`docs/PROJECT_RULES.md`、`docs/SMALL_PAPER_DEV_SPEC.md`、`docs/THESIS_RESEARCH_ROUTE_DRAFT.md`、`docs/handoff.md`、`Documents/论文第三阶段阅读/`、`docs/literature/小论文创新点调研.md`
  - 注意：以上规范文档与 rules 改动需一起整理提交（建议 `docs:` 与 `chore:` 分开两个 commit）
- 工作中 config（含状态 working/frozen）：
  - working 在用：`mmdocir_colpali.yaml`（EXP-002 用的就是它）、`mmdocir_colpali_smoke.yaml`、`mmdocir_bm25_page.yaml`、`mmdocir_dense_page_bge_m3.yaml`、`mmdocir_hybrid_page_bge_m3.yaml`、`mmdocir_layout_node_bge_m3.yaml`（1B 预备）、`demo_page_region.yaml`、`cn_bm25_page.yaml`（frozen test）
  - draft 未接 tasks.ps1：`mmdocir__phase1a__colpali-page-full.yaml`、`mmdocir__phase1a__colpali-page-smoke.yaml`、`mmdocir__phase1a__bm25-page.yaml`（新命名草案，切换前须等价运行验证）
- 最近 commit：`903d1fc exp(mmdocir): record formal ColPali full baseline`（前一条 `fbf596f fix(experiment): isolate MMDocIR smoke and full data`）

## 未解决问题

1. 坐标审计（小论文规范第 6 节）未做：448/32×32 网格与 OCR 绝对像素的对齐是 W 计算的前置硬 Gate，机器门限 + 20 页叠图人工确认都未启动。
2. 新命名 config 草稿未接入 `tasks.ps1`，EXP-002 之后如果切换命名，必须先等价运行验证一次。
3. `docs/literature/12_Bag-of-patches阅读笔记.md` 曾为空文件，Beyond 相关结论引用前需确认已按十段模板补实（大论文规范附录前两项已勾，但文献笔记原文需在场）。
4. 本工作区有大量未提交文档，git 历史与 SSOT 状态行（`docs/00-index.md`）尚未同步新增的三份规范文档。

## 下一步（给新会话的指令）

```text
1. 先提交当前规范文档（.cursor/rules + docs/PROJECT_RULES.md + 三份研究规范 + handoff），commit 拆分：docs(规则类) / chore(.cursor)。
2. 按 docs/SMALL_PAPER_DEV_SPEC.md 第 10.2 节搭脚手架：
   src/mmdocrag/layout/{nodes,correspondence}.py、
   src/mmdocrag/evaluation/{region_metrics,audit}.py、scripts/audit_coords.py、
   tests/{test_correspondence,test_fusion_shapes,test_region_metrics}.py，
   每建一个模块配一个测试，通过 ./tasks.ps1 check。
3. 跑坐标审计 scripts/audit_coords.py：产出 audit.json + ≥20 页叠图，交人工确认表格/栏边界对齐。
4. 审计通过后，用 configs/experiments/mmdocir_layout_node_bge_m3.yaml 与冻结 ColPali Top-K 启动 Phase 1B 的 A/B/C/D 诊断（新建 run_phase1b 脚本 + phase1b config）。
5. 会话结束前更新本文件。
```

## 更新记录

| 日期 | 更新内容 |
| --- | --- |
| 2026-06-16 | 首版：按仓库真实状态填写（EXP-001/002、分支 thesis/structdocir、config 草稿状态、4 条未解决问题、新项目搭建 5 步指令） |
