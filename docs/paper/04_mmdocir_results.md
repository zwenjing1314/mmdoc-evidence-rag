# MMDocIR 公开集验证结果

本文件记录 MMDocIR Evaluation 官方公开集的外部验证，不与中文年报的冻结 test split 混合。数据规模为 313 篇文档、20,395 页、170,338 个布局节点和 1,658 个问题。检索配置为 `search_scope=document`，即使用问题已提供的所属文档，在该文档内部检索页面或布局节点；因此本实验评价的是文档内证据定位，不是跨文档检索。

## 页面级结果

Dense 和 Hybrid 均使用 `BAAI/bge-m3`，`max_length=512`、`batch_size=2`。BM25 结果作为词法基线。

| 方法 | Page R@1 | Page R@5 | Page R@10 | MRR | nDCG@5 | nDCG@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25-page | 0.4903 | 0.7521 | 0.8456 | 0.6084 | 0.6060 | 0.6424 |
| Dense-page (BGE-M3) | 0.4451 | 0.7304 | 0.8263 | 0.5732 | 0.5708 | 0.6095 |
| Hybrid-page (BM25 + BGE-M3) | 0.4879 | **0.7600** | **0.8727** | **0.6143** | **0.6083** | **0.6520** |

Hybrid 相比纯 Dense 在 Page R@5、Page R@10、MRR、nDCG 上均有提升；相比 BM25，Page R@5 提升 0.78 个百分点、Page R@10 提升 2.71 个百分点、MRR 提升 0.59 个百分点。Page R@1 略低于 BM25（0.4879 vs. 0.4903），说明融合主要改善候选页面覆盖和排序后段，而不是第一名命中。

页面级方法不返回 `node_id`，所以 `region_hit@5` 不适用，不应据此比较页面方法的区域能力。

## 运行记录

| 方法 | 配置 | 运行目录 |
| --- | --- | --- |
| BM25-page | `mmdocir_bm25_page.yaml` | `runs/retrieval/mmdocir_bm25_page/20260815_221820` |
| Dense-page | `mmdocir_dense_page_bge_m3.yaml` | `mmdocir_dense_page_bge_m3/20260816_110813` |
| Hybrid-page | `mmdocir_hybrid_page_bge_m3.yaml` | `mmdocir_hybrid_page_bge_m3/20260816_112413` |

## 下一步：布局节点基线

运行 `configs/experiments/mmdocir_layout_node_bge_m3.yaml`，并使用同样的 `--no-sync` 和 CUDA 环境：

```powershell
$env:HF_HOME = "artifacts\hf_cache"
$env:MDR_DENSE_DEVICE = "cuda"
uv run --no-sync mdr retrieve --config configs/experiments/mmdocir_layout_node_bge_m3.yaml
uv run --no-sync mdr evaluate --run runs/retrieval/mmdocir_layout_node_bge_m3/latest
```

MMDocIR 中只有 1,598/1,658 个问题存在精确布局金标，评估输出会额外报告 `region_gold_queries=1598`，布局级 MRR/nDCG 只在这 1,598 个 eligible queries 上计算。

检索日志每行末尾的 `experiment_elapsed` 是从本次实验启动到当前步骤的累计秒数；文档进度中的 `elapsed` 是当前检索循环的局部计时，二者应以 `experiment_elapsed` 作为正式耗时记录。
