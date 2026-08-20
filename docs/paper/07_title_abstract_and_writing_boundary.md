# 小论文题目、摘要与写作边界

## 1. 确定题目

中文题目：**面向中文年报问答的充分性感知多粒度证据集检索方法**

英文题目：**Sufficiency-Aware Multi-Granularity Evidence Set Retrieval for Chinese Annual Report Question Answering**

题目中的“证据集检索”是当前工作的准确边界：系统输出用于支撑回答的多节点证据，不将尚未实现的端到端答案生成、视觉语言模型理解或拒答机制写进题目。

## 2. 实验全过程

1. **数据与标准化表示**：从中文年报 PDF 构建页面、段落、表格块和表格行等混合粒度节点；人工修订 QA 文件作为主实验金标。
2. **固定数据划分**：按公司而非按问题划分 12/4/4 家公司，对应 train/dev/test 的 96/32/32 个问题；测试集及 QA 文件 SHA-256 已冻结。
3. **基线与方法开发**：实现 BM25-page、Dense-page、Hybrid-page、Page-to-Region、Global-Region 等可部署基线，以及 Oracle Page-to-Region 诊断上界。
4. **Evidence Set Region**：结合混合页面候选、全局节点候选、数值扫描和封面锚点，生成候选节点池；再以指标、年份、数值、单位、引用等信息槽位为目标，采用贪心策略选择最多 3 个互补节点。
5. **开发集选择**：在 dev 集上完成候选来源、数值扫描、槽位覆盖和单节点选择等消融，确定最终配置；之后不再依据 test 调参。
6. **冻结测试**：在 32 个 test 问题上报告页面、区域和规则式证据充分性指标。完整方法的 Region Hit@5 与 Sufficiency Rate 均为 0.8750。
7. **节点粒度消融**：验证 paragraph、table block、table row 的单独使用均不如混合节点，完整方法的充分率为 0.8750。
8. **MMDocIR 外部验证**：在 313 篇文档、1,658 个问题上完成 BM25、BGE-M3 Dense、Hybrid 页面检索和 BGE-M3 布局节点检索；并按问题类型分析文本、图表、表格和多模态问题的差异。

## 3. 论文的实验范围

### 可以作为主结论写入

1. 本文研究**已知问题所属文档条件下**的文档内证据检索与定位。
2. 本文方法构建多节点证据集，并以信息槽位覆盖提升财务问答证据的充分性。
3. 数值扫描和槽位覆盖对充分性指标有实证贡献；单节点命中更高不等于证据充分。
4. 混合粒度节点优于单一节点粒度。
5. Hybrid 页面检索在 MMDocIR 的 Page R@5、Page R@10、MRR 和 nDCG 上优于单独 BM25 与 Dense；布局节点检索的区域级结果用于说明细粒度定位难度。
6. 规则式 Sufficiency Rate 是“指标、年份、数值、单位与引用”覆盖的自动检查结果。

### 必须明确限定或避免的表述

1. **不能写**“本文实现通用多模态文档问答”或“能够理解图表视觉语义”。当前 MMDocIR 使用 OCR/VLM 文本和布局节点，不包含图像 embedding 或视觉语言模型推理。
2. **不能写**“本文完成端到端答案生成、答案正确率或幻觉抑制”。当前实现重点是检索、证据集选择和规则式充分性检查，没有正式生成模型实验。
3. **不能写**“本文解决跨文档检索”。所有正式检索配置使用 `search_scope=document`，问题所属文档已知。
4. **不能把 MMDocIR 写成中文年报主方法的直接效果**。它是公开集上的外部页面/布局检索验证，不包含中文财务 Evidence Set 的数值规则。
5. **不能将规则式充分性检查称为人工真值或人类评测**。应写为 automatic rule-based sufficiency verification，并在局限性中说明仍需人工审计。
6. **不能声称统计显著性**。当前 test 只有 32 问，尚未完成置信区间或显著性检验。
7. **避免写“首次”“完全解决”“显著优于”**，除非补充系统性相关工作检索和统计检验。推荐写法是“本文设计”“实验中观察到”“在本数据划分上取得”。

## 4. 中英文摘要

### 中文摘要

长篇中文年报中的财务问答通常需要定位跨页面、跨粒度的证据，单一页面或单一文本片段难以同时覆盖指标名称、报告年度、数值、单位和引用位置，进而导致回答证据不足或引用不一致。针对该问题，本文提出一种面向中文年报问答的充分性感知多粒度证据集检索方法。该方法将页面、段落、表格块和表格行统一表示为证据节点，通过混合页面检索、全局节点检索、结构化数值扫描和封面锚点生成候选集合；随后围绕指标、年份、数值、单位和引用等信息槽位，以贪心策略选择紧凑且互补的证据集，并采用规则式检查评估证据充分性。在按公司划分并冻结的中文年报测试集上，所提方法的 Page Recall@5、Region Hit@5 和 Sufficiency Rate 分别达到 0.8750、0.8750 和 0.8750。消融实验表明，移除数值扫描或槽位覆盖会明显降低证据充分性，且单节点选择虽然具有更高的区域命中率，却难以提供完整支撑。进一步地，在 MMDocIR 公开集上，混合页面检索的 Page Recall@5 达到 0.7600，布局节点检索在具有精确布局标注的问题上取得 0.5044 的 Region Hit@5。结果表明，面向问答的证据检索应关注多节点互补和充分性，而非仅优化单一相关节点命中。

关键词：中文年报问答；证据集检索；多粒度证据；证据充分性；文档检索

### English Abstract

Financial question answering over long Chinese annual reports requires evidence spanning pages and granularities. A single page or text span often fails to jointly cover the metric, reporting year, value, unit, and citation location, resulting in insufficient or inconsistent support. This paper presents a sufficiency-aware multi-granularity evidence set retrieval method for Chinese annual report question answering. Pages, paragraphs, table blocks, and table rows are represented as unified evidence nodes. The method builds a candidate pool through hybrid page retrieval, global region retrieval, structured numeric scanning, and cover-anchor retrieval. It then selects a compact and complementary evidence set using greedy optimization over semantic slots, including metric, year, value, unit, and citation. A rule-based verifier assesses evidence sufficiency. On a frozen company-level Chinese annual report test set, the proposed method achieves 0.8750 Page Recall@5, 0.8750 Region Hit@5, and 0.8750 Sufficiency Rate. Ablation results show that numeric scanning and slot coverage are essential for sufficient evidence, while single-node selection may improve region hits but fails to provide complete support. On the MMDocIR public benchmark, hybrid page retrieval reaches 0.7600 Page Recall@5, and layout-node retrieval obtains 0.5044 Region Hit@5 on queries with exact layout annotations. These results indicate that question answering evidence retrieval should optimize complementary evidence sets and sufficiency rather than only individual relevant-node hits.

Keywords: Chinese annual report question answering; evidence set retrieval; multi-granularity evidence; evidence sufficiency; document retrieval

## 5. 下一节写作顺序

摘要确定后，先写“方法”而不是“引言”。方法部分可依次写：问题定义与符号、混合粒度证据表示、候选生成、槽位覆盖证据集选择、充分性检查。这样每个模块都能直接对应图 1、代码实现和消融实验。
