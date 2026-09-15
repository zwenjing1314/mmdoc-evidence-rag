# MIGRATION.md：旧项目 → 新项目迁移清单

> 用途：新项目创建后，按本清单把旧仓库资产搬过去。搬完一项勾一项。
> 原则：规范文档是"宪法"直接复制；代码是"参考实现"选择性搬运；旧方向资产默认不搬（要时回旧仓库找）。

## 1. 规范与流程文档（直接复制，改目录名引用）

```text
[ ] docs/THESIS_RESEARCH_ROUTE_DRAFT.md    大论文规范（研究边界 SSOT）
[ ] docs/SMALL_PAPER_DEV_SPEC.md           小论文执行规范（方法/公式/实验 SSOT）
[ ] docs/PROJECT_RULES.md                  项目开发规范（Rules，改名为 RULES.md 或保留原名）
[ ] docs/00-index.md                       全仓导航（复制后按新目录改路径）
[ ] docs/01-quickstart.md                  环境与数据准备（改数据根路径说明）
[ ] docs/02-commands.md                    命令手册（改 tasks 脚本名如沿用）
[ ] docs/handoff.md                        交接记录（首版信息重填：新仓库从零开始）
[ ] .cursor/rules/*.mdc                    六条 Cursor 规则（复制后按新包名/新文档名改引用路径）
[ ] .cursor/skills/mmdoc-evidence-research/  研究罗盘 skill（已对齐新主线）
```

## 2. 实验资产（复制，这是半年积累的证据链）

```text
[ ] experiments/registry.csv               实验注册表（EXP-001/002 的唯一凭证）
[ ] experiments/templates/experiment-record.md  11 段记录模板
[ ] experiments/2026-09-12-exp-001-*.md    smoke 记录
[ ] experiments/2026-09-12-exp-002-*.md    full baseline 记录（含页级指标，1B 的分母依据）
[ ] docs/reproduction/colpali_vidore_v1_reproduction_20260830.md  官方复现记录
```

## 3. 配置（选择性复制）

```text
[ ] configs/datasets/mmdocir.yaml          主数据集配置（必搬）
[ ] configs/experiments/mmdocir_colpali.yaml          EXP-002 用的正式 config（必搬）
[ ] configs/experiments/mmdocir_bm25_page.yaml        BM25 对照（必搬）
[ ] configs/experiments/mmdocir_dense_page_bge_m3.yaml    Dense 对照（必搬）
[ ] configs/experiments/mmdocir_hybrid_page_bge_m3.yaml   Hybrid 对照（必搬）
[ ] configs/experiments/mmdocir_layout_node_bge_m3.yaml   1B 预备（必搬）
[ ] configs/README.md                      配置注册表（更新文件名）
[ ] 旧命名 e01-e04、demo、cn_* 系列         默认不搬；新命名草稿三份不搬（新项目直接用新命名）
```

## 4. 代码（参考实现，按新架构重接）

```text
[ ] src/mmdocrag/config.py  paths.py  schemas.py  io.py   骨架：直接搬，改包名
[ ] src/mmdocrag/datasets/adapters.py                      MMDocIR 准备逻辑（必搬，含 313/20395/170338/1658 对数逻辑）
[ ] src/mmdocrag/retrieval/colpali.py                      ColPali 检索器（必搬，embedding cache 逻辑）
[ ] src/mmdocrag/retrieval/{pipeline,scoring}.py           检索管线与打分（搬）
[ ] src/mmdocrag/evaluation/{metrics,pipeline}.py          页级指标（搬；sufficiency.py 是旧方向，不搬）
[ ] src/mmdocrag/exporting/demo.py                         demo 导出（可选）
[ ] src/mmdocrag/cli.py                                    CLI 入口（搬，按新命令重排）
[ ] tests/test_retrieval_metrics.py  test_schemas_io.py  test_data_splits.py  test_colpali_integration.py（搬）
    test_evidence_sufficiency.py  test_cn_annual_reports_v2.py（旧方向，不搬；test_demo_smoke.py 改造后搬）
```

## 5. 数据与产物（不进 git，新机器重新生成）

```text
[ ] data/processed/mmdocir_evaluation/     重跑 prepare 生成（313/20395/170338/1658 必须对数）
[ ] data/interim/mmdocir_evaluation/page_images/  重生成（ColPali 必需）
[ ] artifacts/colpali/ embedding cache     可复制省 8 小时，也可重算
[ ] runs/retrieval/mmdocir_colpali/20260912_221714/  EXP-002 正式 run，复制留档（只读）
```

## 6. 文献资料（复制）

```text
[ ] docs/literature/*.md                   12 篇阅读笔记 + 创新点调研（防御草稿）
[ ] Documents/论文第三阶段阅读/            8 篇原文 PDF（项目外目录，单独拷贝）
[ ] docs/30-literature/README.md           一句话五问表
```

## 7. 明确不搬（留在旧仓库归档）

```text
[ ] src/mmdocrag/evaluation/sufficiency.py        旧 evidence set 方向
[ ] cn_annual_reports 相关 config/split/test/docs   被否方向
[ ] docs/90-archive/ 全部                          历史归档（旧仓库本身就是归档）
[ ] docs/10-small-paper/{plan-source-final,roadmap,results-*,README}.md  已并入两份 SSOT
[ ] docs/paper/ 旧四篇                             结论基于旧代码，重跑前不可引用
[ ] docs/freeze-20260912/                          旧仓库冻结凭证，留在原地
[ ] environment.yml                                旧 conda 遗留
```

## 8. 搬迁后第一周任务

```text
1. 新仓库 git init + 首个 commit（规范文档 + skill + rules 全部入库）
2. uv 环境搭建，跑通 uv run --extra colpali 验证 CUDA
3. 数据 prepare 重跑，对数 313/20395/170338/1658
4. ColPali 页级检索重跑（可用旧 embedding cache），复验 R@5≈0.839 视为迁移成功
5. 坐标审计（小论文规范第 6 节），通过后进入 Phase 1B
```
