Beyond Bag-of-Patches: Learning Global Layout via Textual Supervision for Late-Interaction Visual Document Retrieval

一句话总结：它发现以 ColPali / ColQwen 为代表的视觉文档检索都是 `Bag-of-Patches + MaxSim`，只会局部匹配、不会看全局版式，然后在不改推理流程的前提下，给多向量编码器加了一个可学习的全局版式 token，并用纯讲版式的文本描述子在训练时教它什么是全局结构

# 1. 它要解决什么问题

视觉文档检索`VDR`把一页文档当图片，直接学`Query tokens <-> Page patch tokens`的晚交互`Late-Interaction / MaxSim`相似度：

```
s(Q,D) = sum_i max_j Q_i * D_j
```

优点是能抓住表格格子、图表局部、字形等细粒度证据，缺点是：

1. 每个 patch 独立匹配，丢掉了`图和文字的空间关系、跨区域组合`。
2. 实际文档是异构版式：多栏文本 + 表格 + 图 + 列表，相关性往往来自`叙述文本 + 对应图表的联合`，而不是孤立命中。
3. 论文用图1举例：查`东亚太平洋经济形势如何影响全球贸易`，相关页是左栏风险叙事 + 右栏`EAP: Risks`图，干扰页是目录页，虽然有词汇重叠但全局无关，纯 MaxSim 很容易误检。

作者的论点是：这是结构性缺陷，`全局相关性无法从局部相似度加和中恢复出来`，简单的 mean/max/median pooling 也救不回来。

# 2. 核心方法：带文本监督的全局瓶颈

基于 VLLM，以 ColQwen2.5 3B 为底座：

a. 多向量编码器 + 可训练全局 token

文档页编码为 patch 序列 `I in R^{Lp x d}`，再追加一个随机初始化的可学习向量 `gv in R^d`：

```
I' = [I; gv]
```

一起过 VLLM 的 self-attention。`gv`同时看到所有 patch，充当结构瓶颈，学`caption离chart多近、左栏文本对应右栏图`这类跨区域关系，然后和局部 patch 一起存进索引。

b. 文本结构描述子做版式监督

用 GPT-5 对每页离线生成一段描述子，只讲全局组织，不讲细粒度内容，例如：

-  左栏密集段落讲贸易限制，右栏是标题图总结要点，图表展示比较数据和趋势，整体是叙事分析+可视化统计结合的数据驱动排版。

目的是逼全局 token 去学版式，而不是重复局部 patch 的内容。这个描述子只在训练时用，推理时丢掉。

c. 三个损失联合训练

1. `L_retrieval`：标准的 query-patch 晚交互检索损失。
2. `L_global`：视觉全局 token `gv` vs 描述子全局 token `gdesc` 的 InfoNCE，`sij = cos(gi_v, gj_desc)/tau`，in-batch 负例，让不同页的版式语义拉开。描述子文本走同一个 LLM backbone，保证共享语义空间。
3. `L_local`：每个 patch 去对齐描述子 token 中最相关的那个，` -sum_k max_j cos(i_k, e_j)`，让局部也保持结构连贯。

```
L = L_global + L_local + L_retrieval
```

只更新 LoRA adapter + retrieval projection head，vision encoder 和 LLM 主干冻结，开销很小

d. 推理和打分

纯视觉检索，不需要描述子，不增加线上成本。Query 和 Doc 都带上各自的全局 token：`Q in R^{(Lq+1) x d}, D in R^{(Ld+1) x d}`，还是 MaxSim：

```
s(Q,D) = sum_i max_j Q_i * D_j^T
```

# 3.  实验是怎么做的

- 数据：`ViDoRe-v2`的4个域：Economics、Biomedical、ESGH、ESGR，特点是多栏、嵌图、复杂表格。
- 训练：ColPali 的 `118k train + 500 dev`英文 query-page 对，每例离线配一个结构描述子。
- 基线：
  - 同架构同量级：ColPali 2B、ColQwen2.5 3B、ColQwen2.5-T、ColNomic-3B；
  - 大模型/异架构参考：Nemo-3B 4.4B、ColNomic-7B；
  - 自设的 Cross-Context oracle：推理时把视觉 patch + 文本描述子拼接过 VLLM，`ZS`是冻结直接用，`FT`是在同数据上微调，看显式给全局信息的天花板。
- 指标：`nDCG@5、MAP@5`，ViDoRe 默认 `k=5`。
- 实现：ColQwen2.5 预训练权重初始化，6 epoch，batch 128，AdamW `5e-5`，warmup 100步，bfloat16 + gradient checkpointing，单卡 H200，温度 `tau=0.02`。

# 4.  主要结果

平均全部超同门最强基线 ColQwen2.5 `+2.4 nDCG@5，+2.3 MAP@5`，62.7 / 47.3，四数据集 Wilcoxon 显著：

- 增益集中在版式重的 ESGH、ESGR，如 ESGH 从 68.1->73.4 nDCG。
- 3B 打平甚至超过 4.4B Nemo-3B、7B ColNomic，说明结构归纳偏置带来参数效率。而只加 OCR 文本的 ColQwen2.5-T 没用，证明要的是带空间的结构，不是纯文本。
- 不用描述子推理，还能打平/超过推理时要用描述子的 `CrossContext-FT 62.5/47.1`，说明结构已内化为参数化检索先验，而不只是可利用的特征。

消融证明全局和局部缺一不可：

- 去掉局部 patch：`-27.5 nDCG`，细粒度匹配还是主力。
- 去掉全局 token：`-0.3/-0.4`，小而一致，微调后的局部已部分学到结构，但显式 token 在版式重页仍是最优锚点。只去 query 侧或 image 侧都掉，说明是意图和版式的对齐。
- 去掉 `L_global`：`-2.2`，去掉 `L_local`：`-0.9`，全局对齐是更大贡献者。
- mean/max/median pooling 代替学习到的全局向量：大崩，证明朴素聚合会抹掉结构。

消融证明全局和局部缺一不可：

- 去掉局部 patch：`-27.5 nDCG`，细粒度匹配还是主力。
- 去掉全局 token：`-0.3/-0.4`，小而一致，微调后的局部已部分学到结构，但显式 token 在版式重页仍是最优锚点。只去 query 侧或 image 侧都掉，说明是意图和版式的对齐。
- 去掉 `L_global`：`-2.2`，去掉 `L_local`：`-0.9`，全局对齐是更大贡献者。
- mean/max/median pooling 代替学习到的全局向量：大崩，证明朴素聚合会抹掉结构。

Case study 用 ESGH 说明：提升例平均文本区、视觉元素、列表数、词数、空间香农熵都显著高于失败例，越是多区域、异构、分散的页，增益越大。按 GPT-5 把 query 分为 detail-oriented vs layout-oriented 后，在 layout-oriented 上对 Nemo 的优势主要来自 ESGH/ESGR。

# 5.  贡献和定位

作者自述三点：

1. 指出晚交互 MaxSim 缺乏建模页级结构的机制；
2. 引入可学习的全局瓶颈来编码跨区域结构；
3. 证明这种只在训练时用的描述子监督，不用改推理就能稳定提升，尤其在版式丰富页。

和 Related Work 的区别：不是 OCR pipeline，不依赖 OCR/版式检测；不是 LayoutLM 那种单向量理解模型；也不是 CLIP 那种加个 CLS 向量就行，而是为多向量检索训练了一个检索感知的全局表示，用整体页描述子蒸馏结构语义，同时保留局部精匹配。

局限作者也提了：目前还是单页检索，未来要做多页推理；描述子靠 GPT-5 生成，质量决定上限；在以文本为主、细节导向的 Biomedical 上提升小甚至略输给 Nemo。