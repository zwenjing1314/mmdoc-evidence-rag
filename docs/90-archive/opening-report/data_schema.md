# Standard Data Schema

本项目后续所有数据集统一转换成四类表。

## documents.parquet

```text
doc_id
dataset
title
source_path
domain
language
num_pages
metadata
```

## pages.parquet

```text
doc_id
page_id
page_index
page_text
page_image_path
ocr_text
width
height
metadata
```

## nodes.parquet

```text
node_id
doc_id
page_id
node_type
bbox
text
image_path
parent_id
reading_order
source
confidence
metadata
```

## queries.parquet

```text
query_id
dataset
doc_id
question
answer
question_type
evidence_page_ids
evidence_node_ids
evidence_bboxes
is_answerable
metadata
```
