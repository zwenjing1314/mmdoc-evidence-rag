# 00-index（全仓导航 SSOT）

> Status: stable | Scope: 全仓 | SSOT: 是
> 新增/修改任何 SSOT 文档，必须同步更新本表状态行。

## 五类信息去哪找

| 信息类型 | 位置 | SSOT |
| --- | --- | --- |
| 代码 | `src/` `tests/` `scripts/` | - |
| 配置 | `configs/`（注册表 `configs/README.md`） | `configs/README.md` |
| 数据与运行产物 | `data/` `artifacts/` `runs/`（不进 git） | - |
| 稳定规范 | `docs/01/02/03` `docs/10-small-paper/` | 见下行 |
| 一次性记录 | `experiments/` | `experiments/registry.csv` |

## 入门（按顺序读）

1. `docs/01-quickstart.md`（stable, SSOT）：环境 + 数据准备
2. `docs/02-commands.md`（stable, SSOT）：命令唯一入口
3. `docs/03-glossary.md`（stable）：术语

## 现行研究

- `docs/10-small-paper/plan.md`（SSOT）：方向 + Phase Gate
- `docs/10-small-paper/protocol.md`（SSOT）：协议 + 防泄漏
- `docs/10-small-paper/results-dev.md`（引用页 → `docs/paper/02`）
- `docs/10-small-paper/results-test.md`（引用页 → `docs/paper/03`）
- `docs/10-small-paper/roadmap.md`（引用页 → `docs/paper/research_positioning_and_roadmap`）
- `docs/10-small-paper/plan-source-final.md`：拆分源（只读）
- `docs/10-small-paper/method-spec.md` 待 Phase 2 Gate 后再建

## 实验过程

- `experiments/registry.csv`：注册表（EXP-001 历史 smoke、EXP-002 历史 full，均需按当前代码重跑）
- `experiments/templates/experiment-record.md`：11 段模板
- `docs/20-experiments/mmdocir-external.md`：MMDocIR 外部验证引用页（→ `docs/paper/04`）

## 文献与归档

- `docs/30-literature/README.md`：一句话五问表（`docs/literature/` 原位保留待压缩）
- `docs/90-archive/README.md`：6 目录 + 根级 5 篇，只读

## 冻结记录

- `FREEZE-20260912.md` + `FREEZE-*.txt`：tag `archive-before-cleanup-20260912`

## 状态图例

`stable` 长期有效少改；`working` 正在写；`frozen` 冻结只增版本；`archived` 只读。
