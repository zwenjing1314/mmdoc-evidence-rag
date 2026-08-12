# 真实 Dense Retrieval 修改记录

更新时间：2026-05-31

## 1. 修改目的

之前代码中 `dense` 方法采用“双模式”：

```text
优先加载 sentence-transformers 模型；
如果加载失败，静默回退到 TF-IDF。
```

这会导致一个严重问题：

```text
配置文件写的是 BAAI/bge-m3，但实际实验可能只是 TF-IDF fallback。
```

因此本次修改的目标是：

1. 让 dense 检索显式记录实际后端。
2. 允许正式实验要求必须加载真实 embedding 模型。
3. 如果模型缺失，直接报错，不再静默回退。

## 2. 主要修改

修改文件：

```text
src/mmdocrag/retrieval/pipeline.py
tests/test_retrieval_metrics.py
```

修改配置：

```text
configs/experiments/cn_dense_page.yaml
configs/experiments/cn_page_region.yaml
configs/experiments/cn_hybrid_page.yaml
configs/experiments/cn_hybrid_page_region.yaml
configs/experiments/cn_global_region.yaml
configs/experiments/cn_oracle_page_region.yaml
```

## 3. 新增机制

### 3.0 配置项真正生效

本次同时修正了 `page_retriever` 和 `region_retriever` 只写在 YAML 中、但没有真正控制代码的问题。

现在以下配置会被映射到实际检索方法：

```yaml
page_retriever: dense_page
region_retriever: layout_node
region_method: dense
```

其中：

| 配置值 | 实际方法 |
| --- | --- |
| `bm25_page` | `bm25` |
| `dense_page` | `dense` |
| `tfidf_page` | `tfidf` |
| `layout_node` | `dense` |
| `bm25_node` | `bm25` |
| `dense_node` | `dense` |

### 3.1 `ScoreResult`

新增：

```python
@dataclass(frozen=True)
class ScoreResult:
    scores: list[list[float]]
    backend: str
```

它同时返回：

1. 检索分数矩阵。
2. 实际使用的打分后端。

可能的 backend 包括：

```text
bm25
tfidf
dense:tfidf_fallback
dense:sentence_transformers:BAAI/bge-m3
```

### 3.2 `require_model`

正式 dense 实验配置中新增：

```yaml
require_model: true
```

含义：

```text
如果本地无法加载 sentence-transformers 模型，则直接报错。
```

这样可以避免把 TF-IDF fallback 误写成 Dense Retrieval 实验。

### 3.3 Dense 推理参数

由于中文年报页面较长，BGE-M3 在 CPU 上直接编码整页文本会非常慢。本次新增两个配置项：

```yaml
dense_max_seq_length: 128
dense_batch_size: 8
```

含义：

| 配置 | 作用 |
| --- | --- |
| `dense_max_seq_length` | 限制 embedding 模型输入长度，避免整页长文本导致推理过慢 |
| `dense_batch_size` | 控制每批编码文本数量 |

当前正式配置先采用：

```text
BAAI/bge-m3 + max_seq_length=128 + batch_size=8
```

这是速度和实验真实性之间的折中：仍然使用真实 BGE-M3 embedding，但不再让模型编码完整超长页面。

## 4. 当前正式配置

例如：

```yaml
retriever:
  type: dense_page
  search_scope: document
  encoder: BAAI/bge-m3
  require_model: true
  top_k: [1, 5, 10]
```

当前如果没有本地模型，运行：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

会明确报错：

```text
Dense retrieval requires local SentenceTransformer model `BAAI/bge-m3`,
but it could not be loaded.
```

这说明代码已经不再静默回退到 TF-IDF。

## 4.1 当前全量运行情况

已验证：

```bash
uv run python -c "from mmdocrag.retrieval.pipeline import score_texts_with_backend; r=score_texts_with_backend(['营业收入是多少？'], ['营业收入 100 元', '普通说明'], 'dense', 'BAAI/bge-m3', True, 4, 128); print(r.backend); print(r.scores)"
```

输出后端为：

```text
dense:sentence_transformers:BAAI/bge-m3:maxlen=128
```

说明真实 BGE-M3 链路可用。

但在当前机器上：

```text
torch.backends.mps.is_available() = False
```

因此无法使用 Apple GPU/MPS 加速，只能 CPU 推理。全量 20 份年报、5327 页、99304 个节点的 BGE-M3 实验运行时间过长，已手动停止，避免长时间占用机器。

结论：

```text
BGE-M3 可以作为正式模型，但当前本机不适合直接跑完整节点级全量实验；建议先使用较小模型或缩小实验规模验证流程，再在可用 GPU 或更快机器上跑全量。
```

## 5. 如何下载或缓存模型

### 5.1 使用 HuggingFace 下载

如果网络环境允许，可以运行：

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

该命令会将模型下载到 HuggingFace 本地缓存目录。

下载完成后，再运行：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
```

如果加载成功，`predictions.parquet` 中的 `retriever` 字段会出现：

```text
dense:sentence_transformers:BAAI/bge-m3
```

### 5.2 使用较小模型先验证流程

如果 `BAAI/bge-m3` 下载慢或占用空间较大，可以先将配置中的 encoder 改成：

```yaml
encoder: BAAI/bge-small-zh-v1.5
```

然后下载：

```bash
uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
```

该方式适合先验证真实 Dense Retrieval 流程。

### 5.3 使用本地模型路径

如果模型已经下载到某个本地目录，可以直接写绝对路径：

```yaml
encoder: /Users/zhouwenjing/models/bge-m3
require_model: true
```

只要该目录能被 `SentenceTransformer` 加载，就可以作为真实 dense 模型使用。

## 6. 如果只是想临时跑通流程

可以把配置改成：

```yaml
require_model: false
```

此时如果模型不存在，会回退到：

```text
dense:tfidf_fallback
```

但这种结果只能作为离线 fallback 或轻量 baseline，论文中不能称为真正的 Dense Retrieval 或 BGE-M3 实验。

## 7. 当前测试

已新增测试：

1. `test_dense_fallback_backend_is_explicit`
2. `test_dense_require_model_raises_when_model_missing`

已运行：

```bash
uv run ruff check src tests
uv run pytest
```

结果：

```text
All checks passed
18 passed
```

## 8. 下一步建议

接下来应先完成模型缓存，然后重新跑：

```bash
uv run mdr retrieve --config configs/experiments/cn_dense_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_dense_page/latest
```

随后再重新跑：

```bash
uv run mdr retrieve --config configs/experiments/cn_hybrid_page.yaml
uv run mdr evaluate --run runs/retrieval/cn_hybrid_page/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_page_region/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_global_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_global_region/latest
```

```bash
uv run mdr retrieve --config configs/experiments/cn_oracle_page_region.yaml
uv run mdr evaluate --run runs/retrieval/cn_oracle_page_region/latest
```

只有在真实 dense 模型结果稳定之后，才适合继续做 Hybrid 误差分析和 evidence set 实验。
