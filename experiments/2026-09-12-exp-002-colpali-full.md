# EXP-002 ColPali full Phase 1A baseline（历史 run，作废待重跑）

## 1. 实验目的

- Phase 1A 全量 ColPali 页级 baseline，作为 1B 缺口诊断的对照
- Gate：本记录未完成；必须重跑并核验后才能关闭 1A、进入 1B

## 2. 环境

- uv 管理；commit `a870ee2` 下用 `evaluate-mmdocir` 复评通过
- 实验本身产自 2026-08-31（早于冻结），embedding 缓存 `artifacts/colpali/`

## 3. 数据和 split

- 数据集：`mmdocir_evaluation`
- split：无 / 全量文档内检索（`search_scope=document`）
- 规模：预测文件包含 1,658 个 query、30,112 hits；但旧评价时当前处理目录是 6-query smoke，因此旧 metrics 作废

## 4. 配置文件

- `configs/experiments/mmdocir_colpali.yaml`
- `colpali_page, search_scope=document, model=vidore/colpali, top_k=20`
- `image_batch_size=1, query_batch_size=2, score_batch_size=4, use_embedding_cache=true`

## 5. 运行命令

```powershell
./tasks.ps1 mmdocir-full
./tasks.ps1 evaluate-mmdocir -RunId runs/retrieval/mmdocir_colpali/20260831_163643
```

本次仅为历史 run 补登记，未重跑 retrieve；旧评价结果不可复用。

## 6. 代码 commit

- 复评时 `a870ee2`；原始 run 产自 2026-08-31 commit（见 `FREEZE-20260912.md` 前历史）

## 7. 输出目录

- `runs/retrieval/mmdocir_colpali/20260831_163643`（`latest.txt` 指向）
- 备查：`runs/retrieval/mmdocir_colpali/20260831_163043`

## 8. 关键指标（复评原样抄）

- Page R@1/5/10：`NA`（旧评价使用错误的 6-query smoke 数据）
- MRR / nDCG@5 / nDCG@10：`NA`
- Region Hit@5：`NA`（页级方法不返回 `node_id`，不适用）

注意：该指标与 EXP-001 smoke 在本机复评值相同，说明两个旧 run 均为小样本验证性质，不代表 1658 全量问题的正式 baseline。全量 1658 问题的正式 baseline 仍待跑，见第 11 节。

## 9. 错误信息

- 无（复评通过）

## 10. 结果解释

- 支持假设：无，只定 baseline 位置，不验 H1-H4
- A/B/C/D：待 1B 诊断

## 11. 是否可用于论文 + 下一步

- 可用于论文：否（旧评价使用错误数据，且 run 早于当前防护；需重跑 full 确认）
- 下一步：重跑一次 `./tasks.ps1 mmdocir-full` 产出带当前 commit 的新时间戳 run，确认 `hits` 与 query 规模（1658）一致后，再关闭 1A 进入 1B
- Gate：新 run 完成前不跑 1B 诊断
