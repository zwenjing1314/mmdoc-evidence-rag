# 小论文冻结 Test 结果

本记录仅包含公司级 `test` split 的正式结果：4 家公司、32 个问题。数据划分和 QA 文件版本见 `configs/splits/cn_annual_reports_company_v1.yaml`。不得将本表与此前全量 160 问题或 dev 结果混用。

## 1. 主对比实验

| 方法 | Page R@1 | Page R@5 | Page R@10 | MRR | nDCG@5 | Region Hit@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25-page | 0.1250 | 0.4375 | 0.5938 | 0.2657 | 0.2941 | - |
| Dense-page | 0.1562 | 0.4062 | 0.5625 | 0.2730 | 0.2919 | - |
| Hybrid-page | 0.1875 | 0.5938 | 0.7500 | 0.3351 | 0.3850 | - |
| Page -> Region | 0.0938 | 0.3750 | 0.3750 | 0.1208 | 0.0924 | 0.2500 |
| Hybrid-Page -> Region | 0.1250 | 0.5312 | 0.5312 | 0.0885 | 0.0615 | 0.1875 |
| Global-Region | 0.0625 | 0.1250 | 0.1250 | 0.0859 | 0.0567 | 0.1250 |
| **Evidence Set Region** | **0.4688** | **0.8750** | **0.8750** | **0.6104** | **0.4487** | **0.8750** |
| Oracle-Page -> Region | 1.0000 | 1.0000 | 1.0000 | 0.6771 | 0.6390 | 0.9688 |

说明：页面方法没有输出 evidence node，因此 Region Hit@5 不适用。Oracle 使用标注正确页，仅作为诊断上界，不是可部署对比方法。

## 2. 证据充分性与消融

| 方法 | Region Hit@5 | Sufficiency Rate | Partial or Sufficient | Citation Mismatch | Required Item Coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Full Evidence Set** | 0.8750 | **0.8750** | 0.8750 | 0.0938 | **0.9688** |
| w/o Hybrid-page | 0.8438 | 0.8125 | 0.8750 | 0.0938 | 0.9531 |
| w/o Global-region | 0.8750 | 0.8750 | 0.8750 | 0.0938 | 0.9688 |
| w/o Numeric Scan | 0.6875 | 0.6250 | 0.7812 | 0.1875 | 0.9219 |
| w/o Slot Coverage | **0.9375** | 0.4375 | 0.9688 | 0.0000 | 0.8203 |
| Single-node | **0.9375** | 0.5000 | 0.9688 | 0.0000 | 0.8359 |

核心解释：`w/o Slot Coverage` 和 `Single-node` 的 Region Hit@5 更高，但完整充分率显著更低。这表明单一 gold node 命中不能代表返回证据集足以支撑财务问答；本文方法的目标是充分证据集，而不是单节点命中最大化。

## 3. 节点粒度消融

| 节点类型 | Region Hit@5 | Sufficiency Rate | Required Item Coverage |
| --- | ---: | ---: | ---: |
| paragraph-only | 0.2500 | 0.2500 | 0.7422 |
| table_block-only | 0.2500 | 0.1562 | 0.8984 |
| table_row-only | 0.5938 | 0.0938 | 0.6719 |
| **mixed-node（完整方法）** | **0.8750** | **0.8750** | **0.9688** |

混合节点同时保留叙述型段落、表格上下文和精细表格行。仅使用一种节点类型会丢失其他证据形态，不能稳定支持财务问答。

## 4. 对应运行目录

| 结果 | 运行目录 |
| --- | --- |
| BM25-page | `runs/retrieval/cn_bm25_page/test/20260814_235548` |
| Dense-page | `runs/retrieval/cn_dense_page/test/20260815_200952` |
| Hybrid-page | `runs/retrieval/cn_hybrid_page/test/20260815_201104` |
| Page -> Region | `runs/retrieval/cn_page_region/test/20260815_201141` |
| Hybrid-Page -> Region | `runs/retrieval/cn_hybrid_page_region/test/20260815_201233` |
| Global-Region | `runs/retrieval/cn_global_region/test/20260815_201326` |
| Full Evidence Set | `runs/retrieval/cn_evidence_set_region/test/20260815_201518` |
| Oracle-Page -> Region | `runs/retrieval/cn_oracle_page_region/test/20260815_201812` |
| w/o Hybrid-page | `runs/retrieval/cn_evidence_set_region_wo_hybrid_page/test/20260815_201854` |
| w/o Global-region | `runs/retrieval/cn_evidence_set_region_wo_global_region/test/20260815_202139` |
| w/o Numeric Scan | `runs/retrieval/cn_evidence_set_region_wo_numeric_scan/test/20260815_202335` |
| w/o Slot Coverage | `runs/retrieval/cn_evidence_set_region_wo_slot_coverage/test/20260815_202617` |
| Single-node | `runs/retrieval/cn_evidence_set_region_single_node/test/20260815_202937` |
| paragraph-only | `runs/retrieval/cn_evidence_set_region_paragraph_only/test/20260815_211531` |
| table_block-only | `runs/retrieval/cn_evidence_set_region_table_block_only/test/20260815_211802` |
| table_row-only | `runs/retrieval/cn_evidence_set_region_table_row_only/test/20260815_211945` |

## 5. 当前边界

1. test 仅含 32 个问题，主表应补充 bootstrap 置信区间或配对显著性检验。
2. 充分性评价是规则式“指标-年份-单位-数值-引用”检查，应增加人工抽样审计。
3. 仍需完成至少一个公开数据集验证，才适合作为小论文的完整实验部分。
