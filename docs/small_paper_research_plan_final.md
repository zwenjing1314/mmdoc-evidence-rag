# 小论文研究思路最终版

> 版本性质：当前实验与论文写作的工作版本。最终方法、损失和贡献表述必须以消融实验和独立测试结果为准。

## 1. 暂定题目

中文：**面向视觉文档证据检索的布局约束文档侧 Patch 融合方法**

英文：**Layout-Constrained Document-Side Patch Fusion for Visual Document Evidence Retrieval**

题目暂不绑定 ColPali，便于后续迁移到 ColPali-family backbone。若实验最终只在 ColPali 上完成，可在正文中说明其为 ColPali-compatible 方法。

## 2. 研究背景与问题

ColPali 将页面编码成视觉 patch 多向量，并使用 query-token 与 page-patch 的 MaxSim 完成页面检索。该机制擅长从长文档中找出相关页面，但原始页面 patch 表示没有显式利用 OCR 文本、布局区域边界和区域类型。

已有路线各有局限：

- **Snappy-style 方法**主要在推理阶段把 patch 相关性传播到已有 OCR/Layout BBox，不改变文档表示；
- **ColParse**依赖布局解析、区域裁剪和局部图像重复编码；
- **RegionRAG**训练 query 与视觉 patch 的区域级对齐，并在推理时动态分组显著 patch；
- **Beyond Bag-of-Patches**已经说明可以通过训练让 late-interaction 表示学习布局信息，因此本文不能再声称“首次学习布局表示”。其方法使用 GPT-5 生成的全局结构描述、可学习 global token 和全局/局部结构对齐；它不等同于本文拟研究的 OCR/BBox 区域节点到局部原始 patch 的显式空间软融合。

因此，本研究拟回答：

> 在不裁剪区域图像、不重复运行视觉编码器并保持 ColPali/MaxSim 检索接口的条件下，能否利用 OCR 文本、布局区域边界和区域类型，对原始视觉 patch 学习布局约束的局部增量表示，从而改善页面内证据区域定位，同时控制额外计算成本？

该问题是待验证假设，不预先声称 MMDocIR 上一定存在稳定缺口，也不预先保证新模块一定优于规则方法。

## 3. 方法定位与边界

最终方法定位为：**稀疏的、文档侧的、布局约束 patch 融合**。

“文档侧”表示页面融合向量在离线建库时生成，与 query 无关：

```text
页面图片 + OCR/Layout 信息 -> P_fused（离线缓存）
query -> Q
Q 与 P_fused -> MaxSim 页面/区域检索
```

这保留了 ColPali 的多向量索引接口和较低在线开销，但不能根据不同 query 动态改变文档表示。该限制应在论文中如实讨论，并将 query-conditioned 方法（如 Argus-Retriever）作为相关工作或未来方向。

## 4. 候选网络结构

### 4.1 原始视觉 patch

页面图像经过 ColPali 视觉编码器得到：

```text
P = {p_1, ..., p_N}
```

第一版冻结 ColPali 主干，只训练新增模块；是否加入 LoRA，必须由数据规模、显存和第一阶段结果决定。

### 4.2 OCR/Layout 区域节点

每个布局节点包含：

```text
OCR 文本 + 区域类型 + 归一化 BBox 坐标 (x, y, w, h)
```

通过轻量文本编码器、类型 embedding 和坐标 MLP 得到区域表示：

```text
T_j = Project([Text_j; Type_j; BBox_j])
```

OCR 特征必须经过投影层映射到可与 ColPali patch 交互的空间，不能仅因维度相同就直接相加。

### 4.3 Patch-Region 软对齐

根据 patch 与 BBox 的空间关系构造权重：

```text
W_ij = overlap(patch_i, region_j)
```

开发阶段比较三种定义：

- patch coverage = intersection / patch area；
- region coverage = intersection / region area；
- IoU = intersection / union。

只允许在独立 dev 集确定最终规则，测试集不能调参。必须先审计图像 resize、padding、patch 网格与 BBox 坐标是否一致。

### 4.4 稀疏局部 Cross-Attention

不能默认计算全部 `N × M` 的全连接注意力。对每个 patch，只选择空间重叠或邻近的最多 `K` 个区域节点：

```text
patch p_i
 -> 选择重叠/邻近的 K 个区域
 -> 以 W_ij 作为 attention bias 或 soft mask
 -> 得到增量 Delta_i
```

`K`、邻域规则和空区域处理方式应在 dev 集固定。软约束优先于硬零掩码，以免边界 patch 被突然切断。

### 4.5 门控残差更新

```text
Delta_P = W_zero(SparseCrossAttention(P, T, W))
P_fused = P + Gate(P, Delta_P) * Delta_P
```

Gate、Residual 和 zero-initialization 是稳定训练设计，不单独宣称为算法创新。零初始化的目标是让训练初始状态接近原始 ColPali，降低 OCR 噪声破坏原检索能力的风险；是否有效必须通过消融验证。

## 5. 区域评分与防泄漏规则

页面级分数仍使用 MaxSim：

```text
S_page = MaxSim(Q, P_fused)
```

区域分数使用 patch 对区域的软归属权重聚合。一个 patch 同时覆盖多个 BBox 时，必须规定权重归一化，避免无控制的重复计分。

推理候选 BBox 只能来自 OCR/Layout 解析结果，不能使用 query-specific gold evidence BBox。gold BBox 仅用于最终评测。预测区域与 gold 区域使用预先声明的 IoU 匹配准则，例如 IoU >= 0.5。

## 6. 实验路线

### Phase 1A：数据与页级基线

在当前项目中固定数据版本、图像预处理、候选页面、随机种子和评价脚本，复核 BM25、BGE-M3、Hybrid 与 ColPali 的页级结果。

### Phase 1B：页面—区域缺口诊断

统计以下情况：

- 页面命中且证据区域命中；
- 页面命中但证据区域未命中；
- ColPali 页面未命中、其他方法命中；
- 页面和区域均失败。

保存 query、Top-K 页面、gold 页面、gold 区域、预测区域、分数和可视化案例。至少分析一组成功与失败样例，并按区域类型、面积和 OCR 密度分层。

### Phase 1C：无训练区域 baseline

实现并比较：

1. Snappy-style patch relevance 到已有 BBox 的分数传播；
2. 固定 BBox soft aggregation；
3. 基于 patch relevance map 的动态显著区域分组。

第三项不能称为 RegionRAG 复现，因为它不包含 RegionRAG 的训练期全局/局部对齐和区域监督。

### Decision Gate：是否进入网络训练

只有同时满足以下条件，才进入 Phase 2：

- 页面命中但区域未命中是稳定且有意义的现象；
- 固定 BBox 和动态显著区域 baseline 未充分解决该问题；
- 坐标映射、区域匹配和评价协议已验证；
- 存在独立训练数据及明确的区域标签/伪标签构造方法；
- 新模块的显存、训练和建库成本在硬件可承受范围内。

如果规则方法已经接近解决问题，论文应转向失败类型和效率分析，不为满足“改网络”而强行堆叠模块。

### Phase 2：可学习融合

先冻结 ColPali，只训练 OCR/Layout 投影、稀疏融合层和 Gate。候选损失为：

```text
L = lambda_page * L_page
  + lambda_region * L_region
  + lambda_distill * L_distill
```

其中页面损失保持页级检索，区域损失优化同页内证据区域排序，蒸馏损失约束融合表示不要严重破坏原始 ColPali 排序。损失权重和训练策略均需通过 dev 集确定。

## 7. 对比实验与指标

### 方法对比

```text
BM25
BGE-M3 Dense
Hybrid
ColPali
ColPali + Snappy-style propagation
ColPali + fixed BBox aggregation
ColPali + OCR/Layout projection
ColPali + sparse layout-constrained fusion
Full model + page/region/distillation loss
```

### 指标

- 页面级：Recall@1、Recall@5、MRR、nDCG@5；
- 区域级：Region Recall@1/5、Region MRR、IoU Hit@0.5；
- 效率：向量数量、索引大小、离线编码/融合时间、在线 query 延迟、Top-K 重排时间、峰值显存。

### 必要消融

去掉 OCR、去掉 BBox soft bias、去掉区域类型/坐标、hard mask 与 soft mask、不同 overlap 定义、去掉 Gate、去掉蒸馏，以及不同稀疏邻域大小 `K`。

## 8. 可使用的创新表述

### 方法贡献

> 本文提出一种布局约束的稀疏文档侧 patch 融合模块。在保持 late-interaction/MaxSim 检索接口的条件下，利用 OCR 文本、区域类型、坐标信息及 patch-BBox 软空间对应关系，对原始视觉 patch 进行局部可学习的增量更新，无需裁剪区域图像并重复运行视觉编码器。与已有全局结构描述或 global-token 方法不同，本方法显式建模布局节点与局部 patch 的空间对应关系，并面向页面内证据区域定位进行评估。

### 实证贡献

> 本文在 MMDocIR 的统一协议下，系统分析页级检索与证据区域定位之间的差距，并比较无训练区域分数传播、固定布局聚合和可学习文档侧融合在精度、定位和计算成本上的适用边界。

不建议使用“首次”“填补空白”“显著优于所有方法”等表述，除非完成充分查重并得到统计显著、独立测试结果。Gate、残差、zero-init、BBox 映射、统一评价和避免重复编码不应单独列为创新点。

## 9. 相关工作核对清单

正式投稿前必须精读并记录 Beyond Bag-of-Patches：是否使用 OCR、是否使用 BBox、布局信息注入位置、是否更新局部 patch、是否使用局部跨模态注意力、是否报告区域级定位。

同时明确区分：

- RegionRAG：训练型视觉 patch 区域对齐与动态分组；
- Snappy：推理期已有 BBox 分数传播；
- ColParse：布局裁剪与重复视觉编码；
- Argus-Retriever：query-conditioned region-aware late interaction；
- 本文候选：query-independent、文档侧、OCR/Layout 节点到原始 patch 的稀疏软融合。

## 10. 当前立即执行的任务

1. 在 `colpali` 环境跑通 MMDocIR smoke test；
2. 固定并记录页级 baseline 的配置、数据版本和评价结果；
3. 完成坐标与 patch 网格审计；
4. 设计 Phase 1B 的页面—区域诊断输出格式；
5. 诊断结果确认后，再实现无训练区域 baseline。

当前不训练最终网络、不锁死损失权重、不声称方法已经有效。
