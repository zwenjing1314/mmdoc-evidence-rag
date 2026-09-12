# EXP-001 ColPali smoke（流程验证，不作正式结果）

## 1. 头信息

- EXP-ID: EXP-001
- 日期：2026-09-12（最新 run；另有 2026-08-31 三个历史 run）
- 阶段：Phase 1A（smoke）
- 数据集 + split + query 数：`mmdocir_evaluation` / 无 split / 小样本（`run_info.hits=30`）
- Config：`configs/experiments/mmdocir_colpali_smoke.yaml`（`colpali_page, search_scope=document, model=vidore/colpali, top_k=5`）
- Run 目录：`runs/retrieval/mmdocir_colpali_smoke/20260912_123624`（`latest.txt` 指向；Windows 下为 `latest.txt`）
- 后端：`colpali_page`
- 代码 commit：`2f8587f`（冻结提交；实验本身产自更早 commit，见 `FREEZE-20260912.md`）
- 命令：`./tasks.ps1 mmdocir-smoke`

## 2. 指标（`metrics.json` 原样抄）

- Page R@1/5/10：`0.8333 / 1.0 / 1.0`
- MRR / nDCG@5 / nDCG@10：`0.9167 / 0.8945 / 0.8945`
- Region Hit@5：`0.0`（页级方法不返 `node_id`，不适用）

## 3. 产物清单

- `config.json` / `run_info.json` / `metrics.json` / `predictions.parquet` / `errors.csv` / `summary.md`：齐全
- 归档清单：`../mmdoc-evidence-rag-runs-meta-20260912/runs-list.txt`

## 4. 结论与下一步

- 结论：`prepare → retrieve → evaluate` 链路可跑；CPU 拒绝、缺图报错等保护逻辑符合 `colpali.py` 设计
- 不可用于论文：小样本 smoke，仅流程验证
- 下一步：EXP-002 `./tasks.ps1 mmdocir-full` 全量 `top_k=20` baseline
- Gate：EXP-002 完成前不进入 Phase 1B
