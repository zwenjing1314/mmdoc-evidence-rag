# Parquet 文件从 0 到 1：认识到使用

这篇笔记用于理解本项目为什么大量使用 `.parquet` 文件，以及如何读取、查看、生成和调试 parquet 数据。

## 1. Parquet 是什么

Parquet 是一种用于存储表格数据的文件格式。

你可以先把它理解成：

```text
CSV 的高级版本
```

但它和 CSV 有几个重要区别：

| 对比项 | CSV | Parquet |
|---|---|---|
| 存储方式 | 按行存储纯文本 | 按列存储二进制 |
| 是否保存字段类型 | 不保存 | 保存 |
| 文件大小 | 通常较大 | 通常更小 |
| 读取部分列 | 不方便 | 很方便 |
| 适合大数据 | 一般 | 很适合 |
| 可读性 | 人眼可直接看 | 需要工具读取 |

本项目的数据像这样：

```text
MMDocIR_pages.parquet    约 1.6GB
MMDocIR_layouts.parquet  约 2.5GB
```

这种规模如果用 CSV，会更大、更慢，也更容易丢失字段类型。所以官方数据集使用 parquet 是合理的。

## 2. 为什么 Parquet 适合本项目

本项目处理的是文档智能数据，不是普通小表格。每一行可能是一页文档，也可能是一个 layout 区域。

例如 MMDocIR 的页面表包含：

```text
doc_name
domain
passage_id
image_path
image_binary
ocr_text
vlm_text
```

其中：

- `doc_name` 是字符串；
- `passage_id` 是页面编号；
- `image_binary` 是图片二进制；
- `ocr_text` 是 OCR 文本；
- `vlm_text` 是视觉语言模型生成的文本。

如果用 CSV 保存 `image_binary` 这种二进制字段会非常麻烦；Parquet 则可以直接保存。

MMDocIR 的 layout 表还包含：

```text
bbox
page_size
```

这些是 list 类型。Parquet 也能保存 list，而 CSV 通常只能把它们变成字符串。

## 3. 行存储和列存储的区别

CSV 是按行存储的。

假设有三列：

```text
doc_name,page_id,ocr_text
```

CSV 大概这样存：

```text
doc1,1,text...
doc1,2,text...
doc2,1,text...
```

如果你只想读取 `doc_name` 和 `page_id`，CSV 也通常要扫描整行。

Parquet 是按列存储的。它更像这样：

```text
doc_name: doc1, doc1, doc2
page_id: 1, 2, 1
ocr_text: text..., text..., text...
```

所以只读取部分列时，Parquet 会更快。

在本项目中，如果只做页面检索，可能只需要：

```text
doc_name
passage_id
ocr_text
vlm_text
```

不需要读取巨大的 `image_binary`。这就是 Parquet 的优势。

## 4. 本项目里的 Parquet 文件

### 4.1 原始数据中的 Parquet

MMDocIR 官方数据包含：

```text
data/raw/mmdocir/MMDocIR_pages.parquet
data/raw/mmdocir/MMDocIR_layouts.parquet
```

它们来自官方数据集。

### 4.2 项目处理后的 Parquet

本项目会把不同数据集统一转换成四张标准表：

```text
data/processed/{dataset}/documents.parquet
data/processed/{dataset}/pages.parquet
data/processed/{dataset}/nodes.parquet
data/processed/{dataset}/queries.parquet
```

例如 demo 数据集会生成：

```text
data/processed/demo/documents.parquet
data/processed/demo/pages.parquet
data/processed/demo/nodes.parquet
data/processed/demo/queries.parquet
```

这四张表是后续检索、评估、生成的统一入口。

## 5. 如何查看 Parquet 的字段

本项目使用 `polars` 读取 parquet。

查看字段：

```bash
uv run python - <<'PY'
import polars as pl

path = "data/raw/mmdocir/MMDocIR_pages.parquet"
schema = pl.scan_parquet(path).collect_schema()
print(schema)
PY
```

说明：

- `scan_parquet` 是惰性读取，不会立刻把整个大文件读进内存；
- `collect_schema` 只查看 schema，适合大文件；
- 这一步很快，也比较安全。

## 6. 如何查看前几行

查看前 2 行：

```bash
uv run python - <<'PY'
import polars as pl

path = "data/raw/mmdocir/MMDocIR_pages.parquet"
df = pl.scan_parquet(path).head(2).collect()
print(df)
PY
```

如果文件很大，不要直接：

```python
pl.read_parquet(path)
```

因为这会把整个文件读进内存。

建议优先用：

```python
pl.scan_parquet(path)
```

然后 `.select(...)`、`.filter(...)`、`.head(...)`，最后 `.collect()`。

## 7. 如何只读取部分列

例如只看页面文本：

```bash
uv run python - <<'PY'
import polars as pl

path = "data/raw/mmdocir/MMDocIR_pages.parquet"
df = (
    pl.scan_parquet(path)
    .select(["doc_name", "passage_id", "ocr_text", "vlm_text"])
    .head(5)
    .collect()
)
print(df)
PY
```

这样不会读取 `image_binary` 这种很大的字段。

## 8. 如何过滤某个文档

例如只看某个文档的页面：

```bash
uv run python - <<'PY'
import polars as pl

path = "data/raw/mmdocir/MMDocIR_pages.parquet"
doc_name = "2310.05634v2"

df = (
    pl.scan_parquet(path)
    .filter(pl.col("doc_name") == doc_name)
    .select(["doc_name", "passage_id", "ocr_text"])
    .collect()
)
print(df)
PY
```

这对调试 MMDocIR adapter 很重要。

## 9. 如何写 Parquet

项目里的写入逻辑在：

```text
src/mmdocrag/io.py
```

简化示例：

```python
import polars as pl

rows = [
    {"doc_id": "doc1", "title": "示例文档"},
    {"doc_id": "doc2", "title": "另一个文档"},
]

pl.DataFrame(rows).write_parquet("documents.parquet")
```

读取回来：

```python
df = pl.read_parquet("documents.parquet")
print(df)
```

## 10. 本项目为什么要把 JSON/List 转成字符串

项目中的一些字段是复杂类型，比如：

```text
metadata
bbox
evidence_page_ids
evidence_node_ids
evidence_bboxes
```

它们可能是 dict 或 list。

为了让写入和读取更稳定，`src/mmdocrag/io.py` 里会先把这些字段转换成 JSON 字符串，读取时再转回来。

这样做的好处是：

- 不同 parquet 引擎之间兼容性更好；
- 复杂字段不会因为类型推断失败而报错；
- 后续检查和调试更可控。

## 11. 本项目处理 Parquet 的代码位置

相关文件：

```text
src/mmdocrag/io.py
src/mmdocrag/schemas.py
src/mmdocrag/datasets/adapters.py
```

其中：

- `schemas.py` 定义每一行应该长什么样；
- `io.py` 负责读写 parquet；
- `adapters.py` 负责把原始数据转换成标准 parquet。

## 12. Parquet 在实验流程中的位置

当前流程是：

```text
raw data
  ↓
prepare
  ↓
processed parquet
  ↓
retrieve
  ↓
predictions.parquet
  ↓
evaluate
  ↓
metrics.json / summary.md / errors.csv
```

也就是说：

- `prepare` 负责生成标准 parquet；
- `retrieve` 读取标准 parquet 并生成检索结果 parquet；
- `evaluate` 读取检索结果 parquet 并计算指标。

## 13. 常见问题

### 13.1 为什么不能双击打开 parquet

Parquet 是二进制格式，不是给人直接看的。需要用 Python、Polars、Pandas、DuckDB 等工具读取。

### 13.2 为什么 parquet 比 CSV 小

因为 parquet 会压缩数据，并且按列存储。相同类型的数据放在一起，更容易压缩。

### 13.3 为什么读取 parquet 有时候很慢

可能是因为读取了不必要的大字段，比如 `image_binary`。调试时尽量只 select 需要的列。

### 13.4 为什么本项目要统一成四张 parquet

因为不同数据集格式不一样。如果每个数据集都直接进入检索代码，后续会非常混乱。

统一成：

```text
documents / pages / nodes / queries
```

之后，检索代码就不用关心数据来自 MMDocIR 还是中文年报。

## 14. 你现在最需要掌握的 Parquet 操作

当前阶段最重要的是会做这几件事：

1. 查看 schema：

```python
pl.scan_parquet(path).collect_schema()
```

2. 看前几行：

```python
pl.scan_parquet(path).head(5).collect()
```

3. 只读必要列：

```python
pl.scan_parquet(path).select(["doc_name", "ocr_text"]).head(5).collect()
```

4. 过滤某个文档：

```python
pl.scan_parquet(path).filter(pl.col("doc_name") == doc_name).collect()
```

5. 写入 parquet：

```python
pl.DataFrame(rows).write_parquet(path)
```

掌握这些，就可以开始精修 MMDocIR 的数据适配器。

