# EXP-001 ColPali smoke（流程验证，不作正式结果）

## 1. 实验目的

- 验证 `prepare → retrieve → evaluate` 链路可跑（Phase 1A smoke）
- Gate：smoke 通过后才允许跑 EXP-002 全量 baseline

## 2. 环境

- uv 管理，`pyproject.toml + uv.lock`（见 `FREEZE-20260912.md`）
- ColPali 需 `uv sync --extra colpali` + CUDA/MPS；CPU 被 `colpali.py` 拒绝属预期行为

## 3. 数据和 split

- 数据集：`mmdocir_evaluation`
- split：无 / 小样本（`run_info.hits=30`）
- 数据版本：MMDocIR 外部集，313 文档 / 20395 页 / 170338 节点 / 1658 问题（见 `docs/01-quickstart.md` 第 4 节）

## 4. 配置文件

- `configs/experiments/mmdocir_colpali_smoke.yaml`
- `colpali_page, search_scope=document, model=vidore/colpali, top_k=5`

## 5. 运行命令

```powershell
./tasks.ps1 mmdocir-smoke
```

## 6. 代码 commit

- 冻结提交 `2f8587f`（实验本身产自更早 commit，见 `FREEZE-20260912.md`）

## 7. 输出目录

- `runs/retrieval/mmdocir_colpali_smoke/20260912_123624`（`latest.txt` 指向；Windows 下为 `latest.txt` 而非软链接）

## 8. 关键指标（`metrics.json` 原样抄）

- Page R@1/5/10：`0.8333 / 1.0 / 1.0`
- MRR / nDCG@5 / nDCG@10：`0.9167 / 0.8945 / 0.8945`
- Region Hit@5：`0.0`（页级方法不返 `node_id`，不适用）

## 9. 错误信息

- 无（链路跑通）

## 10. 结果解释

- 支持假设：无，只验流程，不验 H1-H4
- A/B/C/D：不适用（小样本）

## 11. 是否可用于论文 + 下一步

- 可用于论文：否（smoke 一律否）
- 下一步：EXP-002 `./tasks.ps1 mmdocir-full` 全量 `top_k=20` baseline；EXP-002 完成前不进入 Phase 1B
