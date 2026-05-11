# 真实数据接入与运行说明

本文档说明三件事：

1. 当前桌面数据是如何接入项目的。
2. MMDocIR 目录里的文件分别是什么，为什么 `doc_miscellaneous` 里是压缩包。
3. 接下来应该运行哪些命令，以及每条命令的作用。

## 1. 当前数据是如何放进项目的

项目里的数据入口是：

```text
data/raw/mmdocir/
data/raw/cn_annual_reports/pdfs/
```

真实数据原来在桌面：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset
/Users/zhouwenjing/Desktop/DataSets
```

没有把它们完整复制到项目里，而是用了**软链接**。

软链接可以理解为“快捷方式”：

- 项目目录里能看到文件；
- 代码可以像访问普通文件一样访问它们；
- 真实数据仍然保存在桌面原位置；
- 不会重复占用磁盘空间。

例如：

```text
data/raw/mmdocir/MMDocIR_pages.parquet
```

实际指向：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet
```

可以用下面命令查看软链接目标：

```bash
readlink data/raw/mmdocir/MMDocIR_pages.parquet
readlink data/raw/mmdocir/MMDocIR_layouts.parquet
readlink data/raw/mmdocir/doc_miscellaneous
```

中文年报也是同理，例如：

```text
data/raw/cn_annual_reports/pdfs/比亚迪：2025年年度报告.pdf
```

实际指向：

```text
/Users/zhouwenjing/Desktop/DataSets/比亚迪：2025年年度报告.pdf
```

## 2. 为什么使用软链接而不是复制

原因主要是 MMDocIR 很大：

```text
/Users/zhouwenjing/Desktop/DataSets                  约 85MB
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset 约 10GB
```

如果把 MMDocIR 复制到项目里，会额外占用约 10GB 空间。使用软链接后，项目可以正常读取数据，但不会重复存一份。

如果以后移动或删除桌面上的原始数据，项目里的软链接会失效。此时需要重新建立软链接，或者把数据真实复制进项目目录。

## 3. MMDocIR 当前在项目里的结构

当前项目里能看到：

```text
data/raw/mmdocir/MMDocIR_annotations.jsonl
data/raw/mmdocir/MMDocIR_pages.parquet
data/raw/mmdocir/MMDocIR_layouts.parquet
data/raw/mmdocir/README.md
data/raw/mmdocir/doc_miscellaneous/
```

这不是“只复制了一个子文件夹”。实际情况是：

- `MMDocIR_annotations.jsonl` 是问题和证据标注。
- `MMDocIR_pages.parquet` 是页面级数据。
- `MMDocIR_layouts.parquet` 是区域/版面级数据。
- `README.md` 是官方数据说明。
- `doc_miscellaneous/` 是官方提供的辅助压缩包目录。

其中前三个文件才是当前实验最重要的数据。

## 4. MMDocIR 各文件的作用

### 4.1 `MMDocIR_annotations.jsonl`

这是标注文件。它包含 313 个文档的问答标注。

每一行对应一个文档，主要字段包括：

```text
doc_name
domain
page_indices
layout_indices
questions
```

其中 `questions` 里包含：

```text
Q               问题
A               答案
type            问题涉及的模态类型
page_id         正确证据页
layout_mapping  正确证据区域 bbox
```

这个文件会用于生成项目标准表：

```text
queries.parquet
```

也就是实验中的问题、答案和证据标注。

### 4.2 `MMDocIR_pages.parquet`

这是页面级数据，官方说明有 20,395 个页面。

主要字段包括：

```text
doc_name
domain
passage_id
image_path
image_binary
ocr_text
vlm_text
```

当前最小闭环主要会使用：

```text
doc_name
domain
passage_id
ocr_text
vlm_text
```

它会转换成项目标准表：

```text
pages.parquet
```

用于页面级检索，例如 BM25-page、Dense-page。

### 4.3 `MMDocIR_layouts.parquet`

这是区域/版面级数据，官方说明有 170,338 个 layout。

主要字段包括：

```text
doc_name
domain
page_id
layout_id
type
text
ocr_text
vlm_text
bbox
page_size
image_path
image_binary
```

它会转换成项目标准表：

```text
nodes.parquet
```

用于区域级证据定位，例如 Layout-node 和 Page -> Region。

### 4.4 `doc_miscellaneous/`

这个目录里是一些 `.rar` 压缩包：

```text
doc_pdfs.rar
page_images.rar
page_content.rar
layout_images.rar
layout_text_images.rar
layout_content.rar
```

这不是项目漏解压，而是官方本来就这样发布。

根据 MMDocIR 官方 README，这些文件属于 miscellaneous document-related files：

> They are not required in MMDocIR inference and encoding.

也就是说，当前最小实验闭环不必须解压这些 rar。

它们的用途是：

- `doc_pdfs.rar`：原始 PDF。
- `page_images.rar`：页面截图 JPEG。
- `page_content.rar`：每个文档的页面级 jsonl 内容。
- `layout_images.rar`：表格/图像区域裁剪图。
- `layout_text_images.rar`：文本/公式区域裁剪图。
- `layout_content.rar`：每个文档的 layout 级 jsonl 内容。

当前我们先使用 parquet 文件里的文本、OCR、VLM 文本和 bbox 信息，不急着解压这些 rar。

## 5. 目前已经验证过的数据接入状态

中文年报目录已经接入 20 个 PDF：

```bash
find data/raw/cn_annual_reports/pdfs -maxdepth 1 -type l | wc -l
```

结果是：

```text
20
```

MMDocIR 顶层数据已经接入 5 个软链接：

```bash
find data/raw/mmdocir -maxdepth 1 -type l | wc -l
```

结果是：

```text
5
```

中文年报已经成功运行过：

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

输出结果：

```text
documents = 20
pages = 20
nodes = 20
queries = 0
```

这里 `queries = 0` 是正常的，因为中文年报的问题标注还没有填写。

## 6. 接下来第一阶段不要直接全量跑 MMDocIR

MMDocIR 的文件很大：

```text
MMDocIR_pages.parquet    约 1.6GB
MMDocIR_layouts.parquet  约 2.5GB
```

当前代码里的 `mmdocir` 适配器还是通用探测版，如果直接全量读取，可能会比较慢，也可能因为字段适配不够精确而产物不理想。

所以接下来建议按这个顺序：

1. 先检查字段和少量样本。
2. 专门修改 MMDocIR 适配器。
3. 用 `--limit-docs` 先跑小样本。
4. 确认四张标准表正确。
5. 再跑 BM25 和 Page -> Region。

## 7. 推荐运行命令与作用

下面所有命令都在项目根目录运行：

```bash
cd /Users/zhouwenjing/Documents/WorkTransfer/mmdoc-evidence-rag
```

### 7.1 先确认 demo 流程还正常

```bash
uv run mdr prepare --dataset demo
```

作用：

- 生成内置 demo 数据。
- 输出标准四张表。
- 用于确认代码环境和 CLI 没问题。

输出位置：

```text
data/processed/demo/documents.parquet
data/processed/demo/pages.parquet
data/processed/demo/nodes.parquet
data/processed/demo/queries.parquet
```

继续运行：

```bash
uv run mdr retrieve --config configs/experiments/demo_page_region.yaml
```

作用：

- 在 demo 数据上运行 Page -> Region 两阶段检索。
- 先召回页面，再定位区域节点。

输出位置：

```text
runs/retrieval/demo_page_region/latest/predictions.parquet
```

继续运行：

```bash
uv run mdr evaluate --run runs/retrieval/demo_page_region/latest
```

作用：

- 计算 Page Recall、MRR、nDCG、Region Hit。
- 生成错误分析和案例 summary。

输出位置：

```text
runs/retrieval/demo_page_region/latest/metrics.json
runs/retrieval/demo_page_region/latest/errors.csv
runs/retrieval/demo_page_region/latest/summary.md
```

继续运行：

```bash
uv run mdr export-demo --run runs/retrieval/demo_page_region/latest
```

作用：

- 将实验指标导出为开题展示表。

输出位置：

```text
artifacts/figures/opening_experiment_table.md
```

### 7.2 登记中文年报 PDF

```bash
uv run mdr prepare --dataset cn_annual_reports --limit-docs 20
```

作用：

- 扫描 `data/raw/cn_annual_reports/pdfs/` 下的 20 个 PDF。
- 生成文档登记表。
- 当前阶段先生成 placeholder page/node。

输出位置：

```text
data/processed/cn_annual_reports/documents.parquet
data/processed/cn_annual_reports/pages.parquet
data/processed/cn_annual_reports/nodes.parquet
data/processed/cn_annual_reports/queries.parquet
```

注意：

当前中文年报还没有 QA 标注，所以 `queries.parquet` 是空的。后续需要填写：

```text
data/raw/cn_annual_reports/qa_annotations_template.csv
```

或者创建：

```text
data/raw/cn_annual_reports/qa_annotations.csv
```

### 7.3 检查 MMDocIR 字段

先不要直接全量 prepare。先运行下面命令检查字段：

```bash
uv run python - <<'PY'
import json
import polars as pl
from pathlib import Path

root = Path("data/raw/mmdocir")

print("annotations sample:")
with (root / "MMDocIR_annotations.jsonl").open("r", encoding="utf-8") as f:
    obj = json.loads(next(f))
    print(obj.keys())
    print(obj["doc_name"])
    print(obj["questions"][0].keys())

print("\npages schema:")
print(pl.scan_parquet(root / "MMDocIR_pages.parquet").collect_schema())

print("\nlayouts schema:")
print(pl.scan_parquet(root / "MMDocIR_layouts.parquet").collect_schema())
PY
```

作用：

- 确认 annotation、pages、layouts 的字段。
- 为修改 MMDocIR 适配器做准备。

### 7.4 修改 MMDocIR 适配器后再跑小样本

等适配器改好后，先跑：

```bash
uv run mdr prepare --dataset mmdocir --limit-docs 5
```

作用：

- 只处理 5 个文档。
- 避免一开始全量处理 313 个文档导致调试成本太高。
- 生成 MMDocIR 的标准四张表。

输出位置：

```text
data/processed/mmdocir/documents.parquet
data/processed/mmdocir/pages.parquet
data/processed/mmdocir/nodes.parquet
data/processed/mmdocir/queries.parquet
```

### 7.5 跑 MMDocIR 页面级 BM25 baseline

```bash
uv run mdr retrieve --config configs/experiments/e01_bm25_page.yaml
```

作用：

- 在 MMDocIR 标准数据上运行页面级 BM25 检索。
- 回答“只用 OCR/VLM 文本做页面检索，能不能找到正确证据页”。

输出位置：

```text
runs/retrieval/e01_bm25_page/latest/predictions.parquet
```

继续评价：

```bash
uv run mdr evaluate --run runs/retrieval/e01_bm25_page/latest
```

作用：

- 计算真实 MMDocIR 小样本上的 Page Recall、MRR、nDCG。

重点查看：

```text
runs/retrieval/e01_bm25_page/latest/summary.md
runs/retrieval/e01_bm25_page/latest/errors.csv
```

### 7.6 跑 MMDocIR Page -> Region

```bash
uv run mdr retrieve --config configs/experiments/e04_page_region.yaml
```

作用：

- 运行页面级粗召回 + 区域级细定位。
- 对应论文主线“页面-区域协同检索”。

继续评价：

```bash
uv run mdr evaluate --run runs/retrieval/e04_page_region/latest
```

继续导出展示表：

```bash
uv run mdr export-demo --run runs/retrieval/e04_page_region/latest
```

输出位置：

```text
artifacts/figures/opening_experiment_table.md
```

## 8. 最小闭环的验收标准

开题前，最小闭环应该至少拿到这些东西：

```text
data/processed/mmdocir/documents.parquet
data/processed/mmdocir/pages.parquet
data/processed/mmdocir/nodes.parquet
data/processed/mmdocir/queries.parquet
```

以及：

```text
runs/retrieval/e01_bm25_page/latest/metrics.json
runs/retrieval/e01_bm25_page/latest/summary.md
runs/retrieval/e04_page_region/latest/metrics.json
runs/retrieval/e04_page_region/latest/summary.md
artifacts/figures/opening_experiment_table.md
```

这时就可以向老师说明：

1. 已经接入 MMDocIR 和中文年报数据。
2. 已经完成统一数据标准化。
3. 已经跑通页面级检索 baseline。
4. 已经跑通页面-区域两阶段检索。
5. 已经有初步指标和案例分析。

## 9. 当前最重要的下一步

当前最重要的不是解压 rar，也不是跑生成模型，而是：

> 根据 MMDocIR 的真实字段，精修 `src/mmdocrag/datasets/adapters.py` 里的 `prepare_mmdocir`。

精修目标是让它准确生成：

```text
documents.parquet
pages.parquet
nodes.parquet
queries.parquet
```

等这一步完成后，再跑真实检索表。