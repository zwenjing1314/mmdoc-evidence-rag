from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

import polars as pl
from pydantic import BaseModel

from mmdocrag.schemas import DocumentRecord, EvidenceNode, PageRecord, QueryRecord, RetrievalHit

T = TypeVar("T", bound=BaseModel)

JSON_COLUMNS = {
    "metadata",
    "bbox",
    "evidence_page_ids",
    "evidence_node_ids",
    "evidence_bboxes",
}


def _jsonify(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


# 将JSON格式的字符串反序列化为Python对象
def _unjsonify(key: str, value: Any) -> Any:
    if key in JSON_COLUMNS and isinstance(value, str) and value:
        try:
            return json.loads(value)  # json.loads(json_string) 将JSON格式的字符串反序列化为Python对象
        except json.JSONDecodeError:
            return value
    return value

"""
1.准备数据：有一堆 Pydantic 对象（如 DocumentRecord）。
2.序列化：调用 .model_dump() 把它们变成普通的 Python 字典。
3.建表：pl.DataFrame(rows) 把这些字典变成一个整齐的表格。
4.存盘：.write_parquet(path) 把这个表格永久保存到硬盘。
"""
def write_records(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        rows.append({key: _jsonify(value) for key, value in record.model_dump(mode="json").items()})
    pl.DataFrame(rows).write_parquet(path)


"""
总结流程图
1.硬盘上的文件 (xxx.parquet)
 ↓ pl.read_parquet()
2.Polars DataFrame (高性能表格结构)
 ↓ .to_dicts()
3.原始字典列表 (可能有 JSON 字符串混杂其中)
 ↓ _unjsonify() 循环处理
4.cleaned 字典列表 (所有字段都变成了正确的 Python 类型)
 ↓ model(**row)
5.最终结果 (list[DocumentRecord] 等标准对象)
这种写法既保证了读取速度（靠 Polars），又保证了数据的准确性和可用性（靠 _unjsonify 和 Pydantic）
"""
"""
_unjsonify 的作用
这个辅助函数会检查每个字段：
    1.如果这个值是一个看起来像 JSON 的字符串，它就把它解析回 Python 对象（字典或列表）。
    2.如果它已经是普通字符串或数字，就保持不变。
举例说明：
    - 原始 row: {"node_id": "n1", "bbox": "[80.0, 120.0, 520.0, 140.0]"} (bbox 是字符串)
    - 经过 cleaned 处理后: {"node_id": "n1", "bbox": [80.0, 120.0, 520.0, 140.0]} (bbox 变回了列表)
"""
def read_records(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required table: {path}")
    rows = pl.read_parquet(path).to_dicts()
    cleaned = [{key: _unjsonify(key, value) for key, value in row.items()} for row in rows]
    return [model(**row) for row in cleaned]


# 将 4 类数据写进相关的文件夹下 data/processed/cn_annual_reports
def write_processed_dataset(
    processed_dir: Path,
    documents: list[DocumentRecord],
    pages: list[PageRecord],
    nodes: list[EvidenceNode],
    queries: list[QueryRecord],
) -> None:
    write_records(processed_dir / "documents.parquet", documents)
    write_records(processed_dir / "pages.parquet", pages)
    write_records(processed_dir / "nodes.parquet", nodes)
    write_records(processed_dir / "queries.parquet", queries)


# 一次性把该数据集下的 4 张表（文档、页面、节点、查询）全部读进来
def read_processed_dataset(
    processed_dir: Path,
) -> tuple[list[DocumentRecord], list[PageRecord], list[EvidenceNode], list[QueryRecord]]:
    return (
        read_records(processed_dir / "documents.parquet", DocumentRecord),
        read_records(processed_dir / "pages.parquet", PageRecord),
        read_records(processed_dir / "nodes.parquet", EvidenceNode),
        read_records(processed_dir / "queries.parquet", QueryRecord),
    )


def write_hits(path: Path, hits: list[RetrievalHit]) -> None:
    write_records(path, hits)


def read_hits(path: Path) -> list[RetrievalHit]:
    return read_records(path, RetrievalHit)
