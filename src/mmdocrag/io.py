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


def _unjsonify(key: str, value: Any) -> Any:
    if key in JSON_COLUMNS and isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def write_records(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        rows.append({key: _jsonify(value) for key, value in record.model_dump(mode="json").items()})
    pl.DataFrame(rows).write_parquet(path)


def read_records(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required table: {path}")
    rows = pl.read_parquet(path).to_dicts()
    cleaned = [{key: _unjsonify(key, value) for key, value in row.items()} for row in rows]
    return [model(**row) for row in cleaned]


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
