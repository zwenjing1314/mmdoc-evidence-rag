# 当前中文年报检索实验结果表

更新时间：2026-06-01

本文档用于整理当前已经完成的中文年报检索实验结果，后续新增实验时可以继续追加。

## 1. 实验数据

当前实验数据集：

```text
cn_annual_reports
```

当前数据规模：

| 数据表 | 数量 |
| --- | ---: |
| documents | 20 |
| pages | 5327 |
| nodes | 99304 |
| queries | 160 |

当前检索设定：

```text
单文档内部检索，即每个问题只在所属年报内部检索。
```

## 2. 当前实验结果

| 方法 | Page Recall@1 | Page Recall@5 | Page Recall@10 | MRR | nDCG@5 | nDCG@10 | Region Hit@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25-page | 0.0813 | 0.2812 | 0.4062 | 0.1784 | 0.0747 | 0.0908 | 0.0000 |
| Dense-page | 0.1062 | 0.2938 | 0.3937 | 0.1826 | 0.1998 | 0.2323 | 0.0000 |
| Hybrid-page | 0.0875 | 0.3375 | 0.5625 | 0.1979 | 0.2099 | 0.2820 | 0.0000 |
| Page→Region | 0.0813 | 0.2500 | 0.2500 | 0.1150 | 0.0850 | 0.0850 | 0.1875 |
| Hybrid-Page→Region | 0.0625 | 0.3563 | 0.3563 | 0.0728 | 0.0569 | 0.0569 | 0.1938 |
| Global-Region | 0.1250 | 0.2625 | 0.2625 | 0.1711 | 0.1184 | 0.1184 | 0.2562 |
| Evidence Set Region | 0.4250 | 0.8125 | 0.8125 | 0.5529 | 0.4405 | 0.4405 | 0.8063 |
| Oracle-Page→Region | 1.0000 | 1.0000 | 1.0000 | 0.7018 | 0.6712 | 0.6712 | 0.9812 |

## 3. 方法说明

| 方法 | 含义 | 作用 |
| --- | --- | --- |
| BM25-page | 关键词页面级检索 | 基础关键词 baseline |
| Dense-page | 语义页面级检索 | 页面召回 baseline |
| Hybrid-page | BM25 与 Dense 页面召回结果用 RRF 融合 | 检验关键词与语义融合是否提升页面召回 |
| Page→Region | 先 Dense 页面召回，再在候选页内检索节点 | 检验两阶段证据定位 |
| Hybrid-Page→Region | 先 Hybrid 页面召回，再在候选页内检索节点 | 检验融合页面召回对区域定位的影响 |
| Global-Region | 不经过页面召回，直接在整篇文档所有节点中检索 | 判断直接区域检索效果 |
| Evidence Set Region | 合并 Hybrid-page 页面内节点、Global-Region 节点、结构化数值扫描候选和首页锚点，再按覆盖度选择最小证据集 | 检验“候选池召回 + 数值定位 + 证据充分性选择”是否提升区域定位 |
| Oracle-Page→Region | 使用 gold evidence pages 作为候选页，再做区域检索 | 判断区域定位能力上限 |

## 4. 当前观察

1. `Hybrid-page` 的 Page Recall@10 达到 0.5625，高于 `BM25-page` 和 `Dense-page`，说明 BM25 与 Dense 融合能够扩大页面候选覆盖。
2. `Page→Region` 和 `Hybrid-Page→Region` 的 Region Hit@5 分别为 0.1875 和 0.1938，说明简单“两阶段页面到区域检索”可以跑通，但细粒度证据定位能力有限。
3. `Global-Region` 的 Region Hit@5 为 0.2562，高于普通 Page→Region，说明直接节点检索能绕开部分页面召回错误。
4. `Evidence Set Region` 经过数值定位增强和引用一致性修正后，Region Hit@5 达到 0.8063，明显高于 `Hybrid-Page→Region` 和 `Global-Region`，说明“Hybrid-page 页面候选 + Global-region 节点候选 + 结构化数值扫描 + 首页锚点 + 覆盖度选择”的候选证据集方法有效。
5. `Oracle-Page→Region` 的 Region Hit@5 达到 0.9812，说明如果正确页面已知，当前节点切分和节点级检索有较高上限；普通方法与 oracle 之间的差距仍是后续优化重点。
6. 当前最新结果表明，后续不应只增加 baseline，而应继续围绕 evidence set 的充分性评价、四元组一致性校验和拒答机制展开。

## 5. 当前结论

当前实验已经从单一 baseline 扩展为较完整的检索实验矩阵。

可以支撑以下分析：

```text
页面级检索、直接区域检索、预测页面到区域检索、oracle 页面到区域检索之间的差异。
```

目前最重要的实验发现是：

```text
区域检索本身并非完全无效；当 gold pages 已知时，Region Hit@5 可以达到 0.9812。新增 Evidence Set Region 将 Region Hit@5 提升到 0.8063，说明候选池合并、结构化数值定位和最小充分证据集选择是当前最有价值的改进方向。
```

## 6. 对后续实验的启发

下一步建议优先做：

1. 继续分析 `Evidence Set Region` 的成功和失败样例，明确它相比 single-node baseline 的增益来源。
2. 做 `single-node vs evidence-set` 对比，验证收益来自证据集合选择，而不是单纯增加返回数量。
3. 引入 evidence set 充分性评价，判断返回证据是否覆盖指标、年份、数值和单位。
4. 针对财务问题设计“指标-年份-单位-数值”四元组一致性校验。
5. 在生成前加入证据充分性判断，为后续可信生成和拒答实验做准备。

## 7. 证据充分性评价进展

已新增 `verify-evidence` 命令，对 `Evidence Set Region` 的 Top5 evidence set 进行证据充分性评价：

```bash
UV_CACHE_DIR=.uv-cache uv run mdr verify-evidence --run runs/retrieval/cn_evidence_set_region/latest --top-k 5
```

当前结果：

| 指标 | 数值 |
|---|---:|
| sufficiency_rate | 0.7875 |
| partial_or_sufficient_rate | 0.8938 |
| citation_mismatch_rate | 0.0750 |
| avg_required_item_coverage | 0.9422 |
| sufficient | 126 |
| partial | 17 |
| citation_mismatch | 12 |
| insufficient | 5 |

该结果说明：结构化数值扫描和首页锚点显著改善了证据充分性与引用一致性。当前剩余瓶颈主要集中在少量 `value` 缺失、单位缺失和 citation mismatch 样例。
