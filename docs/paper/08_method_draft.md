# 3 方法

本文方法的总体流程如图 1 所示。系统首先将问题和年报解析结果输入页面、节点及结构化候选生成模块，再将多源候选统一评分，并依据问题槽位构造紧凑证据集。最后通过规则式覆盖与引用一致性检查输出证据状态。图中虚线所示的答案生成属于后续系统环节，不在本文实验范围内。

![图 1 充分性感知多粒度证据集检索框架](../../artifacts/figures/evidence_set_region_architecture.svg)

**图 1 充分性感知多粒度 Evidence Set Region 检索框架。**

## 3.1 任务定义

给定一份中文年报文档 $d$、其页面集合 $\mathcal{P}_d=\{p_1,\ldots,p_m\}$ 以及用户问题 $q$，本文关注已知 $q$ 所属文档的文档内证据检索。文档被解析为混合粒度证据节点集合 $\mathcal{N}_d=\{n_1,\ldots,n_l\}$。每个节点 $n_i$ 至少包含页面标识、节点类型、文本内容和版面坐标等属性。

目标不是只返回一个相关片段，而是检索紧凑证据集 $\hat{\mathcal{E}}_q\subseteq\mathcal{N}_d$，使其在不超过预算 $B$ 的条件下尽可能覆盖回答问题所需的信息项：

$$
\hat{\mathcal{E}}_q=\arg\max_{\mathcal{E}\subseteq\mathcal{N}_d,\;|\mathcal{E}|\leq B}
\operatorname{Rel}(q,\mathcal{E})+\lambda\operatorname{Cov}(q,\mathcal{E}),
$$

其中 $\operatorname{Rel}$ 表示问题与证据的相关性，$\operatorname{Cov}$ 表示证据集对问题所需信息槽位的覆盖程度。本文实验中设置 $B=3$，最终保留 Top-5 结果用于标准检索指标和错误分析。

## 3.2 混合粒度证据表示

传统页面级检索以整页为最小单位，容易混入大量无关文本；仅使用细粒度文本节点又可能丢失表格上下文和单位信息。本文将页面内容表示为段落（paragraph）、表格块（table block）和表格行（table row）三类节点。对于节点 $n_i$，记为：

$$
n_i=(d_i,p_i,t_i,x_i,b_i),
$$

其中 $d_i$ 是文档标识，$p_i$ 是页面标识，$t_i$ 是节点类型，$x_i$ 是节点文本，$b_i$ 是可选的版面坐标。混合粒度表示同时保留叙述性文字、表格整体语境和行级数值信息，为证据互补选择提供候选空间。

## 3.3 多源候选生成

### 3.3.1 混合页面候选

首先在文档页面集合内分别使用 BM25 和 Dense 检索，并采用倒数排名融合（reciprocal rank fusion, RRF）生成页面候选。对于页面 $p$，融合分数为：

$$
s_{\mathrm{page}}(p,q)=\sum_{r\in\{\mathrm{BM25},\mathrm{Dense}\}}
\frac{1}{k+\operatorname{rank}_r(p,q)},
$$

其中 $k$ 为 RRF 平滑常数。取 Top-$K_p$ 页面后，将这些页面内的全部混合粒度节点加入候选池。该步骤保证候选节点与页面级主题相关。

### 3.3.2 全局节点候选与结构化候选

仅依赖页面候选可能遗漏页面检索排序靠后的关键节点。因此，本文额外在同一文档的全部节点上进行 Dense 检索，得到全局节点候选。对于数值型或比较型问题，系统还执行结构化数值扫描：优先保留同时包含指标别名、年份、单位、数值模式或表格语境的节点，并对表格行和表格块给予类型偏置。对于报告标题、年度等首页问题，系统从首页节点中加入封面锚点候选。

最终候选池为：

$$
\mathcal{C}_q=\mathcal{C}_{\mathrm{page}}
\cup\mathcal{C}_{\mathrm{global}}
\cup\mathcal{C}_{\mathrm{numeric}}
\cup\mathcal{C}_{\mathrm{cover}}.
$$

上述候选来源均为确定性检索或规则模块，不依赖人工标注的测试答案。

## 3.4 槽位覆盖感知的证据集选择

### 3.4.1 问题槽位构造与候选评分

从问题中抽取目标槽位集合 $\mathcal{S}_q$。对于中文年报数值问题，槽位包括指标、年份、单位、数值形态和关键词；例如“2024 年营业收入是多少”可形成指标、年份、数值形态等槽位。对每个候选节点 $n$，记其覆盖槽位为 $\Gamma(q,n)\subseteq\mathcal{S}_q$，覆盖率为：

$$
c(q,n)=\frac{|\Gamma(q,n)|}{\max(|\mathcal{S}_q|,1)}.
$$

候选节点的综合分数采用可解释的启发式组合：

$$
g(q,n)=s_{\mathrm{sem}}+s_{\mathrm{page}}+s_{\mathrm{global}}
+s_{\mathrm{numeric}}+s_{\mathrm{cover}}
+\alpha c(q,n)+\beta|\Gamma(q,n)|+s_{\mathrm{loc}}+s_{\mathrm{type}},
$$

其中 $s_{\mathrm{sem}}$ 为 Dense 节点排序分数，$s_{\mathrm{page}}$、$s_{\mathrm{global}}$、$s_{\mathrm{numeric}}$ 和 $s_{\mathrm{cover}}$ 分别来自页面候选、全局节点、数值扫描和封面锚点的排名奖励；$s_{\mathrm{loc}}$ 为数值型问题的表格/版式定位奖励，$s_{\mathrm{type}}$ 为节点类型偏置。该分数不是学习模型的输出，而是用于整合多源证据的固定规则分数。

### 3.4.2 贪心证据集构造

为避免多个高分节点重复表达同一信息，本文按“新增槽位优先”的策略迭代选择节点。在第 $j$ 步，已覆盖槽位集合为 $\mathcal{U}_{j-1}$，选择：

$$
n_j=\arg\max_{n\in\mathcal{C}_q\setminus\mathcal{E}_{j-1}}
\left(
|\Gamma(q,n)\setminus\mathcal{U}_{j-1}|,
c(q,n),
g(q,n)
\right),
$$

其中三元组按字典序比较。随后更新
$\mathcal{E}_j=\mathcal{E}_{j-1}\cup\{n_j\}$ 和
$\mathcal{U}_j=\mathcal{U}_{j-1}\cup\Gamma(q,n_j)$。当槽位全部覆盖、候选耗尽或达到预算 $B$ 时停止。若没有节点被选中，则回退到综合分数最高的节点。该策略优先选择能补充未覆盖信息项的节点，而不是重复选择语义最相近的单一片段。

## 3.5 规则式证据充分性检查

在评测阶段，对输出证据集文本进行规则式检查。对每个问题定义所需项集合 $\mathcal{I}_q$，数值型问题可包含指标、年份、单位和数值；对文本型问题则使用从问题抽取的槽位。证据覆盖率定义为：

$$
\operatorname{Cov}_{\mathrm{req}}(q,\hat{\mathcal{E}}_q)=
\frac{|\{i\in\mathcal{I}_q:i\ \text{is covered}\}|}{|\mathcal{I}_q|}.
$$

评测时，若输出节点与人工标注证据节点有交集，则认为引用一致。仅当所有所需项均被覆盖且引用一致时，样本被标记为 sufficient；所需项完整但引用不一致时标记为 citation mismatch；覆盖率至少为 0.5 时标记为 partial，其余为 insufficient。Sufficiency Rate 是 sufficient 样本占全部问题的比例。

该检查用于评估检索证据是否具备回答支撑条件，不等同于人工判定的答案正确率。其可靠性与局限性将在实验和局限性章节中单独讨论。

## 3.6 实现设置

中文年报实验的 Dense 编码器为 `BAAI/bge-small-zh-v1.5`，最大序列长度为 128，批大小为 8。最终 Evidence Set Region 配置使用 Top-10 页面候选、Top-20 全局节点候选、Top-20 数值扫描候选和最多 3 个证据节点。所有中文主实验均采用已冻结的公司级划分；MMDocIR 外部验证使用 BGE-M3[10]，最大序列长度为 512，批大小为 2，仅用于页面和布局节点检索验证。
