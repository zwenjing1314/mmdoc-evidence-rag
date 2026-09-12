# 文档地图（全仓导航 SSOT）

> Status: stable | Scope: 全仓 | SSOT: 是

## 入门（先看这 3 篇）

- `docs/01-quickstart.md`（stable）：新机器 15 分钟跑通 demo。
- `docs/02-commands.md`（stable, SSOT）：所有命令唯一入口，输入/输出/检查。
- `docs/03-glossary.md`（stable）：page / region / evidence-set / oracle 术语。

## 现行研究（小论文唯一真理源）

- `docs/10-small-paper/`：plan + method-spec + protocol + results-dev/test + roadmap。
- 现状：骨架已建，内容仍以 `docs/small_paper_research_plan_final.md` 和 `docs/paper/` 为准，迁移完成前见各目录 `README.md` 中的映射表。

## 实验过程（只增不改）

- `experiments/registry.csv`：每次正式 run 一行（SSOT）。
- `docs/20-experiments/`：单次实验详情 + 模板。
- `runs/` 不进 Git，只留 `config.json` / `run_info.json` / `metrics.json` 反查。

## 文献与归档

- `docs/30-literature/`：每篇一句话结论 + 与本文关系。
- `docs/90-archive/`：开题遗产只读归档地，不再维护、不再引用。

## 状态图例

`stable` 长期有效少改；`working` 正在写；`frozen` 冻结只增版本；`archived` 只读。
