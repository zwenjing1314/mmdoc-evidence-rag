# Windows 论文执行指南：从 ColPali 复现到毕业论文

## 0. 给接手本项目的 GPT

请按本文档的顺序帮助用户推进，不要一开始设计完整新模型，也不要一次性要求用户理解所有术语。用户目前处于“已经跑通 ColPali，但对后续论文、实验和创新点还不熟悉”的阶段，需要先建立实验理解，再逐步确定方法。

用户目前的真实状态：

- 已完成 ColPali 官方 checkpoint 的推理与 ViDoRe V1 全量评测；
- 还没有复现 ColParse、RegionRAG、MM-Matryoshka；
- 对 Cross-Attention、Gate、LoRA、蒸馏损失、RoI Align 等概念感到陌生；
- 容易因为一次听到太多候选模块而产生迷茫；
- 正式实验主要在 Windows RTX 3080 Ti 12GB 上进行；
- 当前首要任务不是立即发表或训练，而是按顺序完成学习、基线实验、问题诊断和最小方法验证。

每次给用户命令时，必须说明：

1. 应在哪个 Conda 环境执行；
2. 命令的目的；
3. 预期看到什么结果；
4. 如果失败，先检查什么；
5. 不要把候选方案说成已经证实的结论。

## 1. 项目与研究目标

主仓库：

\`\`\`text
C:\\Users\\WenJing\\Documents\\WorkTransfer\\mmdoc-evidence-rag
\`\`\`

主题暂定为：

> 面向多模态长文档的布局感知多向量检索方法研究。

研究基础是 ColPali 的视觉多向量检索；候选研究问题是：

> 在不重复裁剪和视觉编码文档区域的条件下，能否利用 MMDocIR 的布局框和 OCR 信息，对 ColPali 的视觉 patch 表示进行可学习的空间约束融合，从而改善页面内证据区域定位，并分析精度与计算成本的变化？

这只是待验证问题，不是已经证明的结论。

## 2. 已完成的 ColPali 官方复现

官方源码单独保存于：

\`\`\`text
C:\\Users\\WenJing\\Documents\\WorkTransfer\\colpali-official-repro
\`\`\`

使用模型：\`vidore/colpali\`。

使用的基础模型：\`vidore/colpaligemma-3b-mix-448-base\`。

使用的 benchmark：\`vidore-benchmark==5.0.0\`。

使用的 ViDoRe V1 collection：

\`\`\`text
vidore/vidore-benchmark-667173f98e70a1c0fa4db00d
\`\`\`

硬件与环境：

- Windows；
- NVIDIA GeForce RTX 3080 Ti，12 GB；
- Python 3.11；
- \`vidore-eval\` 环境用于官方 ViDoRe 全量评测；
- \`colpali\` 环境用于主项目中的 ColPali 和 MMDocIR 接入。

已得到 10 个 ViDoRe V1 子集的宏平均 \`nDCG@5 = 80.00%\`。官方 README 公开值为 81.3；当前结果应表述为在当前 collection、benchmark 和依赖版本下完成的可复查 GPU 复现，不要直接说复现失败。

官方结果文件在：

\`\`\`text
C:\\Users\\WenJing\\Documents\\WorkTransfer\\colpali-official-repro\\outputs\\colpali_full
\`\`\`

主项目的复现记录：

\`\`\`text
docs/reproduction/colpali_vidore_v1_reproduction_20260830.md
\`\`\`

## 3. 主项目现有代码

主项目原有基础包括：

- MMDocIR 数据适配和统一记录格式；
- 页面、query、布局节点和 gold 读取；
- BM25、BGE-M3 Dense、Hybrid baseline；
- 统一检索评价和结果保存；
- 配置、日志和实验文档规范。

已加入的 ColPali 接入：

| 文件 | 作用 |
|---|---|
| \`src/mmdocrag/retrieval/colpali.py\` | 加载 \`vidore/colpali\`，编码页面图片和 query，计算 MaxSim；要求 CUDA |
| \`src/mmdocrag/retrieval/pipeline.py\` | 注册 \`colpali_page\` 检索类型 |
| \`configs/experiments/mmdocir_colpali.yaml\` | MMDocIR 全量配置 |
| \`configs/experiments/mmdocir_colpali_smoke.yaml\` | 单文档 smoke test 配置 |
| \`src/mmdocrag/datasets/adapters.py\` | 从 MMDocIR parquet 的 \`image_binary\` 生成 JPEG，写入 \`page_image_path\` |
| \`tests/test_colpali_integration.py\` | ColPali 接入测试 |
| \`pyproject.toml\` | 增加 \`.[colpali]\` 可选依赖 |

生成的页面图片：

\`\`\`text
data/interim/mmdocir_evaluation/page_images/
\`\`\`

页面 embedding 缓存：

\`\`\`text
artifacts/colpali/mmdocir_evaluation/vidore_colpali/
\`\`\`

数据、模型、embedding、runs 和 outputs 不提交 Git。

## 4. Windows 当前任务

所有主项目 ColPali 命令在 \`colpali\` 环境执行：

\`\`\`powershell
conda activate colpali
cd C:\\Users\\WenJing\\Documents\\WorkTransfer\\mmdoc-evidence-rag
python -m pip install -e ".[colpali]"
\`\`\`

先检查 CUDA：

\`\`\`powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
\`\`\`

应该显示 CUDA 为 \`True\`，并显示 RTX 3080 Ti。

先跑一份文档：

\`\`\`powershell
mdr prepare --dataset mmdocir --limit-docs 1
mdr retrieve --config configs\\experiments\\mmdocir_colpali_smoke.yaml
mdr evaluate --run runs\\retrieval\\mmdocir_colpali_smoke\\latest
\`\`\`

目的：确认 MMDocIR 数据、页面 JPEG、ColPali、GPU、检索结果和评价接口全部连通。

smoke 成功后，重新准备全量数据：

\`\`\`powershell
mdr prepare --dataset mmdocir
mdr retrieve --config configs\\experiments\\mmdocir_colpali.yaml
mdr evaluate --run runs\\retrieval\\mmdocir_colpali\\latest
\`\`\`

smoke 会覆盖处理后的数据，因此必须重新执行全量 \`prepare\`。

## 5. 阅读阶段：现在先做什么

当前不要训练新网络。按照以下顺序完成阅读：

\`\`\`text
ColParse -> RegionRAG -> MM-Matryoshka
\`\`\`

每篇先只回答五个问题：

\`\`\`text
1. 它解决什么问题？
2. 它改了哪一部分？
3. 是否需要训练？
4. 使用什么数据和指标？
5. 与 ColPali 的真正区别是什么？
\`\`\`

### ColParse

重点理解：

\`\`\`text
MinerU2.5 解析页面
-> 裁剪布局子图
-> 每个子图重新编码 local vector
-> 整页编码 global vector
-> global/local 融合
-> 少量向量检索
\`\`\`

它主要解决布局感知表示和多向量存储成本，不是直接在 ColPali patch 上做可学习 OCR 融合。

### RegionRAG

重点理解：

\`\`\`text
patch 检索
-> 找显著 patch
-> 邻近 patch 分组为视觉区域
-> 只将相关区域交给生成模型
\`\`\`

它是训练型区域级 RAG 方法，重点看 global/local 对齐、区域监督和推理时区域分组。

### MM-Matryoshka

重点理解：

\`\`\`text
训练同时支持不同 encoder layer 和 embedding dimension
-> 推理时按预算选择表示
-> 平衡精度、存储和计算
\`\`\`

它是效率方向，不是当前结构融合核心。

每篇只写一页笔记，模板：

\`\`\`markdown
# 论文名称

## 解决的问题
## 输入与输出
## 方法流程
## 是否训练
## 数据集与指标
## 主要结果
## 局限
## 与 ColPali 的区别
## 对本课题的启发
## 暂时不懂的地方
\`\`\`

目前不要求完整复现这三篇论文。优先阅读和理解，避免时间消耗在多个环境和数据集上。

## 6. 实验诊断阶段

阅读完成后，在 MMDocIR 上先比较已有方法：

\`\`\`text
BM25
BGE-M3 Dense
Hybrid
ColPali
\`\`\`

要求使用相同 query、页面候选、gold 和评价接口。

诊断目标不是立即追求最高分，而是观察 ColPali 的实际失败类型：

| 类型 | 现象 | 意义 |
|---|---|---|
| A | 页面命中，区域也命中 | 原始 ColPali 已足够的样例 |
| B | 页面命中，区域未命中 | 结构区域模块的直接动机 |
| C | ColPali 页面未命中，文本/布局方法命中 | 可能需要 OCR/VLM 融合 |
| D | 页面和区域都失败 | 可能是 query、图片质量或跨页问题 |

至少保存：

- 10 个成功案例；
- 10 个失败案例；
- query、Top-K 页面、gold 页面、gold 区域和预测分数；
- 页面截图和区域可视化。

如果 B 类和 C 类比例很低，不要强行设计复杂结构；应重新缩小问题。

## 7. 最终候选方法

在完成诊断后，才决定是否实现以下方法。它是候选设计，不是预先确定的结论。

### 7.1 主干

保留 ColPali 作为视觉和 query 编码主干。第一版冻结主干，不重新训练整个 PaliGemma。

\`\`\`text
page image -> ColPali -> patch vectors P
query -> ColPali -> query token vectors Q
\`\`\`

### 7.2 Patch-to-Region 软对齐

利用 MMDocIR 的 BBox 建立 patch 与区域的对应关系。第一版使用 patch-BBox IoU 或面积重叠作为软权重：

\`\`\`text
patch P_i + region box B_j
-> overlap weight w_ij
-> region visual representation R_j
\`\`\`

先不要直接使用中心点硬分配，也不要一开始使用 RoI Align。必须先验证图像 resize、padding、patch 网格和 BBox 坐标是否一致。

### 7.3 OCR/Layout 投影

如果诊断表明纯视觉表示需要文字补充，再使用区域 OCR 文本、区域类型和归一化坐标：

\`\`\`text
OCR text + region type + bbox
-> lightweight encoder/MLP
-> T_j
\`\`\`

OCR 特征必须通过投影层映射到可与 ColPali 表示交互的空间，不能因为维度相同就直接相加。

### 7.4 区域约束 Cross-Attention

候选结构：

\`\`\`text
patch P 作为 Query
区域 OCR/Layout T 作为 Key/Value
patch-BBox overlap 作为 attention bias 或 soft mask
-> Delta_P
\`\`\`

使用软权重优先于全零硬掩码，避免边界 patch 被突然切断。

### 7.5 门控残差

推荐形式：

\`\`\`text
Delta_P = W_zero(CrossAttention(P, T, soft_mask))
P_fused = P + Gate(P, Delta_P) * Delta_P
\`\`\`

初始时将 \`W_zero\` 或 Gate 初始化为 0，使 \`P_fused\` 接近原始 \`P\`。不要默认写成 \`LayerNorm(P + ...)\` 后就声称与原模型完全相同，因为 LayerNorm 可能改变表示分布。

无 OCR 的 patch 可以优先采用“跳过 Cross-Attention、保留原始 P”的方式；可学习 null token 仅作为后续对照，不是必须方案。

### 7.6 页面和区域打分

页面分数：

\`\`\`text
S_page = MaxSim(Q, P)
\`\`\`

融合表示分数：

\`\`\`text
S_fused = MaxSim(Q, P_fused)
\`\`\`

区域分数：

\`\`\`text
S_region(j) = MaxSim(Q, patches assigned to region j)
\`\`\`

第一版建议两阶段：先用原始 ColPali 召回页面，再在 Top-K 页面内做区域重排。页面与融合分数融合时必须先归一化，权重只能在 dev 集或预先固定规则上确定。

## 8. 训练计划

当前 MMDocIR 是 evaluation 数据，不能直接用其 gold 训练后又在同一批数据上报告最终测试结果。

### 没有独立训练集时

只做：

\`\`\`text
冻结 ColPali
固定 IoU 区域聚合
固定或规则分数融合
页面级和区域级评价
\`\`\`

### 获得独立训练数据后

分阶段训练：

\`\`\`text
Phase 1：冻结 ColPali，只训练 OCR/Layout 投影和区域融合层
Phase 2：视结果决定是否加入 LoRA 或解冻部分主干
\`\`\`

候选损失：

\`\`\`text
L_page：query-positive page 对比损失
L_region：query-positive region 排序/对比损失
L_distill：融合表示保持原始 ColPali 排序行为
L = lambda1 * L_page + lambda2 * L_region + lambda3 * L_distill
\`\`\`

不能在没有实现和训练数据之前把这组损失写成已经确定的最终方案。

训练区域标签的来源必须标明：

- 强监督：明确提供证据框的数据；
- 弱监督：答案文本与 OCR 框匹配得到的伪标签；
- 页面级监督：只有 query-positive page。

DocVQA、InfoVQA、TAT-DQA 有 query、答案和 OCR/BBox 信息，但不能默认它们天然提供人工答案证据框。使用前必须检查并记录标签构造规则。

## 9. 最小实验表

第一阶段：

\`\`\`text
A. BM25
B. BGE-M3
C. Hybrid
D. ColPali
\`\`\`

方法验证阶段：

\`\`\`text
E. ColPali + Snappy-style score propagation
F. ColPali + fixed IoU region pooling
G. F + OCR/Layout projection
H. G + masked Cross-Attention
I. H + gated residual
\`\`\`

训练阶段（有独立训练集后）：

\`\`\`text
J. I + page/region/distillation loss
\`\`\`

不要只报告最终模型。每增加一个模块，都要说明它解决了哪个观察到的问题。

指标：

\`\`\`text
页面级：Recall@1、Recall@5、nDCG@5、MRR
区域级：Region Recall@1、Region Recall@5、Region MRR 或 IoU 命中率
效率：向量数量、索引大小、编码时间、query 延迟、Top-K 重排时间、显存
\`\`\`

消融至少包括：

\`\`\`text
去掉区域聚合
去掉 OCR
去掉坐标/区域类型
hard mask vs soft mask
平均池化 vs 可学习池化
去掉 Gate
去掉 Distillation
\`\`\`

## 10. 论文写作主线

论文不要写成“把很多模型拼在一起”，而应按以下逻辑组织：

\`\`\`text
ColPali 证明视觉页面多向量检索有效
-> MMDocIR 诊断页面级表示在区域证据定位上的表现
-> 相关工作提供区域传播、局部/全局表示和效率压缩启发
-> 提出一个针对诊断缺口的核心模块
-> 用页面、区域、效率和消融实验验证
\`\`\`

可能的贡献表述：

1. 一种复用 ColPali patch、避免区域重复视觉编码的布局约束融合模块；
2. 一种页面级检索与区域级证据定位的统一评测流程；
3. MMDocIR 上关于视觉、OCR 和布局信息作用的系统分析；
4. 精度、区域定位和索引/推理成本之间的实验权衡。

只有实验支持时，才能声称这些贡献成立。

## 11. 工作停止条件

遇到以下情况时，不要继续堆叠模块：

- 坐标映射无法验证；
- BBox 标注与页面图像不一致；
- 区域标签无法可靠构造；
- 新模块只提升测试集而没有独立 dev 支持；
- 页面指标下降且区域指标没有提升；
- 复杂 Cross-Attention 不优于固定 IoU 聚合；
- 训练成本和数据量超过 Windows GPU 能承受范围。

此时可以把论文范围收缩为：

\`\`\`text
ColPali baseline
+ 区域定位诊断
+ 固定布局聚合方法
+ 页面/区域/效率分析
\`\`\`

## 12. 当前最具体的下一步

只执行下面三件事：

1. 在 Windows \`colpali\` 环境跑通 MMDocIR ColPali smoke test；
2. 读完 ColParse、RegionRAG、MM-Matryoshka 各一页笔记；
3. 在 MMDocIR 上得到 BM25、BGE-M3、Hybrid、ColPali 的第一版对比结果。

完成这三件事后，再决定是否实现 Snappy-style 区域分数传播和固定 IoU 区域聚合。暂时不要训练 Cross-Attention，也不要确定最终论文标题和损失函数。

