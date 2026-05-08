from __future__ import annotations

from mmdocrag.io import read_records, write_records
from mmdocrag.schemas import DocumentRecord, QueryRecord


def test_schema_roundtrip_parquet(tmp_path):
    path = tmp_path / "documents.parquet"
    records = [
        DocumentRecord(
            doc_id="doc1",
            dataset="demo",
            title="Demo",
            language="zh",
            metadata={"source": "unit-test"},
        )
    ]
    write_records(path, records)

    loaded = read_records(path, DocumentRecord)

    assert loaded[0].doc_id == "doc1"
    assert loaded[0].metadata["source"] == "unit-test"


def test_query_defaults_are_lists():
    query = QueryRecord(query_id="q1", dataset="demo", doc_id="doc1", question="收入是多少？")

    assert query.evidence_page_ids == []
    assert query.evidence_node_ids == []
    assert query.is_answerable is True
