# Contributing

> Status: stable | Scope: 全仓 | SSOT: 是（开发流程唯一入口）

## 1. 分支

- `main` 只合可跑版本：`./tasks.ps1 check` 通过。
- 小论文工作用短分支，例如 `paper/phase-1b-diag`。
- 归档分支 `archive/opening-202608` 只读，不再合回 `main`。

## 2. 提交规范

格式：`<type>(<scope>): <subject>`

- `feat(retrieval):` 新检索器/新融合逻辑
- `fix(eval):` 指标、匹配、泄漏修复
- `docs:` 仅文档（SSOT 变更必须说明理由）
- `exp(mmdocir):` 配置/脚本封装（不含大结果文件）
- `chore:` 环境、任务脚本、模板

`runs/`、`data/raw|processed|interim`、`artifacts/` 永不提交（见 `.gitignore`）。

## 3. DoD（完成定义）

一次任务算完成，必须同时满足：

1. `./tasks.ps1 check`（ruff + pytest）通过；
2. 新增/修改的 config 已在 `configs/README.md` 登记状态（working/frozen/deprecated）；
3. 正式 run 有 `config.json` + `run_info.json` + `metrics.json` + `predictions.parquet`；
4. 实验已在 `experiments/registry.csv` 加一行，并在 `docs/20-experiments/` 留记录；
5. `docs/00-index.md` 状态行已更新（如新增 SSOT）。

## 4. Phase Gate（小论文卡点）

- Phase 1B 的 A/B/C/D 四类统计没出来，不许开 1C；
- 1C 三个无训练基线没跑完并记录，不许开 Phase 2 训练；
- `test` 只跑冻结方法和预先声明的消融；按 test 改参必须回 dev 开新版本。

## 5. 禁止新建的文件

禁止新增 `*_change_log.md`、`current_experiment_results.md`、`experiment_progress_and_commands.md` 类流水账：

- 代码为什么改：看 commit + `CHANGELOG.md`；
- 实验得到啥：看 `experiments/registry.csv` + `docs/20-experiments/YYYY-MM-DD-主题.md`；
- 规范变了啥：直接改 SSOT 文档。
