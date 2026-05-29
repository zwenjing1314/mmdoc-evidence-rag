# 相关算法笔记

本文档用于记录项目中用到的核心算法。后续新增算法时，按同样格式继续追加即可。

建议每个算法都按以下结构记录：

1. 解决什么问题
2. 核心思想
3. 关键公式或步骤
4. 优点与局限
5. 本项目中哪里用到

---

## 1. BM25

### 1.1 解决什么问题

BM25 是一种经典的关键词检索算法，用来计算：

```text
一个查询 query 和一篇文档 document 的相关性分数
```

在本项目中，可以理解为：

```text
一个问题 和 一个年报页面 的相关程度
```

分数越高，表示这个页面越可能包含问题答案。

### 1.2 核心思想

BM25 主要考虑三件事：

| 因素 | 含义 |
| --- | --- |
| 词是否匹配 | 查询词出现在文档里，文档更相关 |
| 词的重要性 | 越少见的词越重要，例如公司名、财务指标 |
| 文档长度 | 太长的页面不能因为词多就天然占便宜 |

简单说：

```text
一个页面中出现了问题里的关键词，并且这些关键词比较有区分度，同时页面长度不过分占便宜，那么 BM25 分数就会更高。
```

### 1.3 核心公式

BM25 对一个查询词 `t` 的打分可以简化理解为：

```text
score(t, d) = IDF(t) * 词频饱和项 * 文档长度惩罚项
```

完整形式常写为：

```text
BM25(q, d) = sum IDF(t) * ( tf(t,d) * (k1 + 1) )
                      / ( tf(t,d) + k1 * (1 - b + b * |d| / avgdl) )
```

其中：

| 符号 | 含义 |
| --- | --- |
| `q` | 查询，也就是问题 |
| `d` | 文档，在本项目中通常是一个页面文本 |
| `t` | 查询中的某个词 |
| `tf(t,d)` | 词 `t` 在文档 `d` 中出现的次数 |
| `IDF(t)` | 词 `t` 的逆文档频率，表示这个词有多稀有 |
| `|d|` | 当前文档长度 |
| `avgdl` | 所有文档的平均长度 |
| `k1` | 控制词频增长的饱和程度 |
| `b` | 控制文档长度归一化强度 |

本项目默认参数：

```python
k1 = 1.5
b = 0.75
```

### 1.4 实现步骤

BM25 的计算流程可以分为四步：

1. 对所有页面文本进行分词。
2. 统计每个词出现在多少个页面中，也就是 `df`。
3. 对每个问题，逐个计算它和候选页面的 BM25 分数。
4. 按分数从高到低排序，返回 Top-K 页面。

### 1.5 一个直观例子

问题：

```text
公司的营业收入是多少？
```

页面 A 出现：

```text
营业收入 233,432,768,960.43 元
```

页面 B 出现：

```text
公司治理结构持续完善
```

BM25 会认为页面 A 更相关，因为它包含了问题中的核心词：

```text
营业收入
```

### 1.6 优点与局限

优点：

1. 不需要训练模型。
2. 运行速度快。
3. 结果容易解释。
4. 适合作为检索 baseline。

局限：

1. 依赖关键词匹配，同义表达能力弱。
2. 对中文分词质量敏感。
3. 不能真正理解语义。
4. 很难处理图表、图片和复杂版面信息。

例如：

```text
问题写“营收”，页面写“营业收入”
```

如果没有合适的分词、同义词或语义模型，BM25 可能无法很好匹配。

### 1.7 本项目中哪里用到

#### 1. 配置文件

中文年报 BM25 实验配置位于：

```text
configs/experiments/cn_bm25_page.yaml
```

核心配置：

```yaml
retriever:
  type: bm25_page
  search_scope: document
  top_k: [1, 5, 10]
```

含义：

| 配置 | 作用 |
| --- | --- |
| `type: bm25_page` | 使用 BM25 做页面级检索 |
| `search_scope: document` | 每个问题只在所属年报内部检索 |
| `top_k: [1, 5, 10]` | 评价 Top-1、Top-5、Top-10 命中情况 |

#### 2. 检索入口

代码位置：

```text
src/mmdocrag/retrieval/pipeline.py
```

当配置中写：

```yaml
type: bm25_page
```

程序会进入：

```python
if retriever_type == "bm25_page":
    hits = retrieve_pages(
        queries,
        pages,
        method="bm25",
        top_k=max_top_k(retriever),
        search_scope=search_scope,
    )
```

这里的含义是：

```text
把所有问题 queries 和页面 pages 交给 retrieve_pages，并指定 method="bm25"。
```

#### 3. BM25 打分实现

代码位置：

```text
src/mmdocrag/retrieval/scoring.py
```

核心类：

```python
class SimpleBM25:
```

主要做了三件事：

1. `tokenize(doc)`：对页面文本分词。
2. `self.df.update(set(doc))`：统计每个词出现在多少个页面中。
3. `score(query)`：计算问题和每个页面的 BM25 分数。

#### 4. 实际运行命令

运行 BM25 页面级检索：

```bash
uv run mdr retrieve --config configs/experiments/cn_bm25_page.yaml
```

评价 BM25 检索结果：

```bash
uv run mdr evaluate --run runs/retrieval/cn_bm25_page/latest
```

输出结果主要包括：

```text
runs/retrieval/cn_bm25_page/latest/predictions.parquet
runs/retrieval/cn_bm25_page/latest/metrics.json
runs/retrieval/cn_bm25_page/latest/errors.csv
runs/retrieval/cn_bm25_page/latest/summary.md
```

### 1.8 在论文实验中的角色

BM25 在本文项目中主要作为：

```text
关键词检索 baseline
```

它不是本文的创新点，而是用来对比后续方法：

1. Dense-page 是否比关键词检索更好。
2. Page to Region 是否能在页面召回后进一步定位细粒度证据。
3. 后续 evidence set 和重排序方法是否能超过基础检索方法。

因此，BM25 的价值是：

```text
提供一个简单、可复现、可解释的基础对照实验。
```

---

## 2. TF-IDF

### 2.1 解决什么问题

TF-IDF 也是一种关键词检索和文本相似度方法，用来判断：

```text
一个查询 query 和一段文本 document 是否相关
```

在本项目中，它主要有两个作用：

1. 作为轻量级文本检索方法。
2. 当本地没有可用的向量模型时，作为 Dense Retrieval 的离线 fallback。

### 2.2 核心思想

TF-IDF 由两部分组成：

| 部分 | 含义 |
| --- | --- |
| TF | Term Frequency，词在当前文档中出现得越多，越重要 |
| IDF | Inverse Document Frequency，词在整个语料中越少见，越重要 |

简单说：

```text
一个词在当前页面里经常出现，但在其它页面里不常出现，它就更能代表这个页面。
```

### 2.3 核心公式

TF-IDF 的基本形式是：

```text
TF-IDF(t, d) = TF(t, d) * IDF(t)
```

其中：

```text
IDF(t) = log((N + 1) / (DF(t) + 1)) + 1
```

| 符号 | 含义 |
| --- | --- |
| `t` | 某个词 |
| `d` | 某个文档或页面 |
| `N` | 文档总数 |
| `DF(t)` | 包含词 `t` 的文档数量 |

本项目中，TF 采用词频占比：

```text
TF(t, d) = count(t, d) / 当前文档总词数
```

### 2.4 实现步骤

TF-IDF 的计算流程：

1. 对每个页面文本分词。
2. 统计每个词在多少个页面中出现。
3. 将每个页面转换成 TF-IDF 向量。
4. 将问题也转换成 TF-IDF 向量。
5. 使用余弦相似度计算问题和页面的相似程度。
6. 按相似度从高到低返回 Top-K。

余弦相似度可以理解为：

```text
两个向量方向越接近，文本越相似。
```

### 2.5 优点与局限

优点：

1. 简单、快速、可解释。
2. 不需要训练模型。
3. 离线环境也能运行。
4. 适合作为语义模型不可用时的 fallback。

局限：

1. 本质上仍然依赖词面匹配。
2. 对同义词和语义改写不敏感。
3. 不能理解表格结构、图像和版面信息。
4. 效果通常弱于真正的向量检索模型。

### 2.6 本项目中哪里用到

#### 1. TF-IDF 实现位置

代码位置：

```text
src/mmdocrag/retrieval/scoring.py
```

核心类：

```python
class SimpleTfidf:
```

主要函数：

```python
_vector()
score()
cosine()
```

其中：

| 函数 | 作用 |
| --- | --- |
| `_vector()` | 将文本转换成 TF-IDF 向量 |
| `score()` | 计算一个问题和所有候选文本的相似度 |
| `cosine()` | 计算两个 TF-IDF 向量的余弦相似度 |

#### 2. Dense fallback 中使用

代码位置：

```text
src/mmdocrag/retrieval/pipeline.py
```

当检索方法是：

```python
method == "dense"
```

程序会先尝试加载本地 `sentence-transformers` 模型。如果模型不可用，就回退到：

```python
tfidf = SimpleTfidf(docs)
return [tfidf.score(query) for query in queries]
```

也就是说，当前的 `dense_page` 在没有本地模型时，并不是真正的深度向量检索，而是使用 TF-IDF 保证实验可以离线跑通。

### 2.7 在论文实验中的角色

TF-IDF 在本文项目中的角色是：

```text
轻量级语义检索 fallback / 可复现 baseline
```

它的价值是保证：

1. 没有 GPU 也可以运行。
2. 没有下载大模型也可以运行。
3. 实验流程不会因为模型缺失而中断。

但论文中需要注意表述：

```text
如果当前环境实际使用的是 TF-IDF fallback，就不能把结果直接表述为真正的 BGE-M3 向量检索结果。
```

---

## 3. Dense Retrieval

### 3.1 解决什么问题

Dense Retrieval 是向量检索方法，用来解决传统关键词检索不擅长的问题：

```text
问题和文档表达不同，但语义相近。
```

例如：

```text
问题：公司营收是多少？
页面：营业收入为 233,432,768,960.43 元
```

BM25 可能依赖“营收”和“营业收入”的词面匹配，而 Dense Retrieval 希望通过语义向量识别它们相关。

### 3.2 核心思想

Dense Retrieval 的核心思想是：

```text
用编码模型把问题和文档都转换成向量，再比较向量相似度。
```

流程可以简化为：

```text
query text -> encoder -> query embedding
document text -> encoder -> document embedding
相似度计算 -> 排序 -> Top-K
```

如果两个文本语义接近，它们的向量距离就应该更近。

### 3.3 常见相似度

Dense Retrieval 常用余弦相似度：

```text
cosine(q, d) = q · d / (||q|| * ||d||)
```

其中：

| 符号 | 含义 |
| --- | --- |
| `q` | 问题向量 |
| `d` | 页面或节点向量 |
| `q · d` | 两个向量的点积 |
| `||q||` | 问题向量长度 |
| `||d||` | 文档向量长度 |

相似度越高，表示问题和页面越相关。

### 3.4 实现步骤

Dense Retrieval 的基本流程：

1. 读取问题和候选页面文本。
2. 使用编码模型生成问题向量。
3. 使用同一个编码模型生成页面向量。
4. 计算问题向量和页面向量的相似度。
5. 按相似度排序。
6. 返回 Top-K 页面或节点。

### 3.5 优点与局限

优点：

1. 能捕捉一定的语义相似性。
2. 对同义表达通常比 BM25 更友好。
3. 适合做页面级召回和语义检索。
4. 可以和 BM25、RRF、重排序模型组合使用。

局限：

1. 需要预训练向量模型。
2. 模型下载和运行成本更高。
3. 对长页面文本可能存在截断或信息稀释问题。
4. 如果只输入页面文本，仍然没有真正利用图像和版面信息。

### 3.6 本项目中哪里用到

#### 1. 配置文件

中文年报 Dense-page 实验配置位于：

```text
configs/experiments/cn_dense_page.yaml
```

核心配置：

```yaml
retriever:
  type: dense_page
  search_scope: document
  encoder: BAAI/bge-m3
  top_k: [1, 5, 10]
```

含义：

| 配置 | 作用 |
| --- | --- |
| `type: dense_page` | 使用 dense 页面级检索 |
| `search_scope: document` | 每个问题只在所属年报内部检索 |
| `encoder: BAAI/bge-m3` | 优先使用 BGE-M3 作为向量编码模型 |
| `top_k` | 返回并评价 Top-K 检索结果 |

#### 2. 检索入口

代码位置：

```text
src/mmdocrag/retrieval/pipeline.py
```

当配置中写：

```yaml
type: dense_page
```

程序会进入：

```python
elif retriever_type == "dense_page":
    hits = retrieve_pages(
        queries,
        pages,
        method="dense",
        top_k=max_top_k(retriever),
        encoder=str(retriever.get("encoder", "BAAI/bge-m3")),
        search_scope=search_scope,
    )
```

#### 3. 向量模型尝试加载

代码位置：

```text
src/mmdocrag/retrieval/pipeline.py
```

核心函数：

```python
try_sentence_transformer_scores()
```

它会尝试使用：

```python
SentenceTransformer(model_name, local_files_only=True)
```

也就是优先加载本地模型，不默认联网下载。

如果模型存在：

```text
使用 sentence-transformers 生成 query embedding 和 document embedding，再计算余弦相似度。
```

如果模型不存在：

```text
返回 None，然后自动回退到 SimpleTfidf。
```

### 3.7 实际运行命令

运行 Dense-page 检索：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

评价 Dense-page 检索结果：

```bash
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

主要输出：

```text
runs/retrieval/cn_dense_page/latest/predictions.parquet
runs/retrieval/cn_dense_page/latest/metrics.json
runs/retrieval/cn_dense_page/latest/errors.csv
runs/retrieval/cn_dense_page/latest/summary.md
```

### 3.8 在论文实验中的角色

Dense Retrieval 在本文项目中主要作为：

```text
页面级语义召回 baseline
```

它用来回答：

1. 语义检索是否比 BM25 更适合中文年报页面召回。
2. 后续 Page to Region 是否应该建立在 Dense-page 的候选页面上。
3. 后续引入 BGE-M3、BGE-reranker、ColPali 等模型时，能否进一步提升效果。

需要特别注意：

```text
当前代码是“双模式”：
有本地 sentence-transformers 模型时，使用真正的 dense embedding；
没有本地模型时，自动使用 TF-IDF fallback。
```

所以写实验结果时，要确认当前实际使用的是哪一种模式。

---

## 后续待补充算法

后续可以继续追加：

1. BGE-M3
2. RRF 重排序
3. Page to Region 两阶段检索
4. Evidence Set 选择
5. NLI / LLM Verifier
