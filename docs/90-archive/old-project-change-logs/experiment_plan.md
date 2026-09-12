# Experiment Plan

## Opening Defense Pre-Experiment

先完成大实验的最小闭环：

1. 数据标准化：MMDocIR 小样本 + 20 份中文年报。
2. 检索 baseline：
   - BM25-page
   - Dense-page
   - Layout-aware node
   - Page -> Region
3. 指标：
   - Page Recall@1/5/10
   - MRR
   - nDCG@k
   - Region Hit@k
4. 输出：
   - `runs/retrieval/.../metrics.json`
   - `runs/retrieval/.../predictions.parquet`
   - `runs/retrieval/.../errors.csv`
   - `runs/retrieval/.../summary.md`

## Thesis Full Experiment

后续完整论文实验扩展为：

1. MMDocIR 主检索实验。
2. 中文年报应用验证。
3. LongDocURL 或 MMLongBench-Doc 生成验证。
4. Visual Page Retrieval 与 Hybrid Retrieval。
5. Evidence Cards 证据增强生成。
6. Sufficiency / Support / Abstention 可信验证。
7. 消融实验、效率实验、错误分析。
