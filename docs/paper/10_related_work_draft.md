# 2 相关工作

## 2.1 检索增强问答与文档检索

检索增强生成（Retrieval-Augmented Generation, RAG）通过从外部语料中检索相关证据，再由生成模型利用证据完成知识密集型任务[1]。在检索阶段，BM25 等词法方法依赖词项匹配，具有高效、可解释的特点[2]；稠密检索则通过双编码器将问题和文本映射到连续向量空间，以缓解词面不一致问题[3]。两类信号各有优势，因而常通过级联或融合提高召回稳定性。

长文档场景与开放域文本检索不同：候选内容具有页码、版面、章节和表格等结构，且用户问题常已知其所属文档。直接将整篇文档切分为固定长度文本块，可能破坏页面与表格语境；仅检索整页又会引入冗余内容。本文在已知所属文档的条件下联合使用页面级和节点级检索：混合页面检索用于获得主题相关页面，全局节点检索和结构化数值扫描用于补充页面候选遗漏的细粒度证据。与仅关注单个文本块相关性的工作不同，本文进一步以证据集合为输出对象。

## 2.2 文档结构理解与多模态文档问答

视觉文档理解研究表明，文本内容、二维版面和视觉特征共同影响文档语义建模。LayoutLMv3 通过统一的文本和图像掩码预训练建模文档布局[4]；DocVQA 等基准推动了面向扫描文档图像的视觉问答研究[5]；Donut 等端到端方法则尝试从文档图像直接生成结构化结果或答案[6]。这些工作为处理图表、版面和视觉元素提供了重要基础。

本文与端到端视觉文档问答的目标不同。本文的主任务是中文年报中的文档内证据检索，当前系统使用 PDF 解析得到的页面文本、段落、表格块和表格行节点，不对原始图像进行视觉语言模型编码。因此，本文将图表视觉语义理解、图像内对象识别和图表数值抽取视为后续扩展，而不将其作为已解决能力。MMDocIR 分类型结果中图表类问题的较低节点命中率也支持这一边界。

## 2.3 证据归因、引用与可验证回答

仅有相关上下文并不能保证生成回答受到证据支持。面向引用生成的研究要求模型在输出文本时提供可追溯来源，并从引用正确性和引用完整性等角度评价回答[7]。Self-RAG 等方法进一步将检索、生成和自我反思结合，以改善回答的事实性和可控性[8]。这些研究强调“回答是否被证据支撑”，但其主要目标通常是生成阶段的归因或事实性控制。

本文将关注点前移到检索阶段：在生成前构造能够共同支撑回答的多节点证据集。对于年报数值问答，单个节点即使与问题语义相关，也可能缺少年份、单位或数值，因此本文以指标、年份、数值、单位和关键词等槽位度量候选节点的互补性，并使用规则式充分性检查评估所选证据集。该检查在评测阶段结合人工证据标注计算引用一致性，不应与端到端生成模型的事实性评价混同。

## 2.4 本文定位

综上，现有 RAG 与检索工作为相关文本定位提供基础，视觉文档理解工作为多模态扩展提供可能，引用与事实性研究则强调回答的可验证性。本文的差异在于：

1. 面向中文年报的混合粒度证据表示，保留段落与表格层级的互补信息；
2. 以多源候选生成和槽位覆盖感知选择构造紧凑证据集，而非仅返回单一高分节点；
3. 在冻结公司级测试上同时报告页面、区域和规则式证据充分性指标，并通过 MMDocIR 外部检索验证说明适用范围。

本文不将 BM25、Dense encoder、OCR、表格解析或视觉语言模型本身视为创新；贡献在于面向年报数值问答的证据组织、选择目标和充分性评测设计。

## 参考文献候选

以下条目用于当前草稿编号，投稿前需按目标模板统一格式并核对完整出版信息。

1. Lewis, P., Perez, E., Piktus, A., et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*, 2020.
2. Robertson, S., and Zaragoza, H. The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 2009.
3. Karpukhin, V., Oguz, B., Min, S., et al. Dense Passage Retrieval for Open-Domain Question Answering. *EMNLP*, 2020.
4. Huang, Y., Lv, T., Cui, L., et al. LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking. *ACM Multimedia*, 2022.
5. Mathew, M., Karatzas, D., and Jawahar, C. V. DocVQA: A Dataset for VQA on Document Images. *WACV*, 2021.
6. Kim, G., Hong, T., Yim, M., et al. OCR-free Document Understanding Transformer. *ECCV*, 2022.
7. Gao, T., Yen, H., Yu, J., and Chen, D. Enabling Large Language Models to Generate Text with Citations. *EMNLP*, 2023.
8. Asai, A., Wu, Z., Wang, Y., et al. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. *ICLR*, 2024.
9. Dong, K., Chang, Y., Goh, X. D., Li, D., Tang, R., and Liu, Y. MMDocIR: Benchmarking Multi-Modal Retrieval for Long Documents. *arXiv preprint arXiv:2501.08828*, 2025.
10. Chen, J., Xiao, S., Zhang, P., et al. BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. *arXiv preprint arXiv:2402.03216*, 2024.
