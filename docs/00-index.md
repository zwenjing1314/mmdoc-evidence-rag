# 00-index（全仓导航 SSOT）

> Status: stable | Scope: 全仓 | SSOT: 是
> 新增/修改任何 SSOT 文档，必须同步更新本表状态行。三个月后项目乱不乱，看这张表有没有人维护。

## 五类信息去哪找

| 信息类型 | 位置 | SSOT |
| --- | --- | --- |
| 代码 | `src/` `tests/` `scripts/` | - |
| 配置 | `configs/`（注册表 `configs/README.md`） | `configs/README.md` |
| 数据与运行产物 | `data/` `artifacts/` `runs/`（不进 git） | - |
| 稳定规范 | `docs/01/02/03` `docs/10-small-paper/` | 见下行 |
| 一次性记录 | `experiments/` | `experiments/registry.csv` |

## 入门（按顺序读）

1. `docs/01-quickstart.md`（stable, SSOT）：环境 + 数据准备（uv 主方案 / conda 兜底 / MMDocIR 数据位置）
2. `docs/02-commands.md`（stable, SSOT）：命令唯一入口，命令/输入/输出/检查四件套
3. `docs/03-glossary.md`（stable）：术语

## 现行研究（小论文）

- `docs/10-small-paper/plan.md`（SSOT）：研究方向 + Phase Gate
- `docs/10-small-paper/protocol.md`（SSOT）：评价协议 + 防泄漏
- `docs/10-small-paper/README.md`：其余映射表（method-spec/results 等待建）

## 实验过程

- `experiments/registry.csv`：注册表，一次正式 run 一行
- `experiments/templates/experiment-record.md`：详情模板（11 段）
- `experiments/YYYY-MM-DD-exp-NNN-主题.md`：详情页
- 已登记：EXP-001（smoke，完成）、EXP-002（full，待跑）
- `docs/20-experiments/README.md`：使用规则（即将并入本表，过渡期以 `experiments/` 为准）

## 文献与归档

- `docs/30-literature/README.md`：一句话结论 + 与本文关系
- `docs/90-archive/README.md`：归档区只读（待第 6 步填充）

## 冻结记录

- `FREEZE-20260912.md` + `FREEZE-*.txt`：第 1 步冻结证据，tag `archive-before-cleanup-20260912`

## 状态图例

`stable` 长期有效少改；`working` 正在写；`frozen` 冻结只增版本；`archived` 只读。
