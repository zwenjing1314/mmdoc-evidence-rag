from __future__ import annotations

import pytest

from mmdocrag.evaluation.pipeline import load_run_queries
from mmdocrag.io import write_processed_dataset
from mmdocrag.retrieval.pipeline import apply_data_split
from mmdocrag.schemas import DocumentRecord, EvidenceNode, PageRecord, QueryRecord


def _records():
    documents = [
        DocumentRecord(doc_id="doc_train", dataset="demo"),
        DocumentRecord(doc_id="doc_dev", dataset="demo"),
        DocumentRecord(doc_id="doc_test", dataset="demo"),
    ]
    pages = [PageRecord(doc_id=item.doc_id, page_id=f"{item.doc_id}_p1", page_index=1) for item in documents]
    nodes = [
        EvidenceNode(doc_id=item.doc_id, page_id=f"{item.doc_id}_p1", node_id=f"{item.doc_id}_n1")
        for item in documents
    ]
    queries = [
        QueryRecord(query_id=f"q_{item.doc_id}", dataset="demo", doc_id=item.doc_id, question="问题")
        for item in documents
    ]
    return documents, pages, nodes, queries


def _manifest(tmp_path):
    path = tmp_path / "split.yaml"
    path.write_text(
        """
dataset: demo
test_status: frozen
splits:
  train: [doc_train]
  dev: [doc_dev]
  test: [doc_test]
""".strip(),
        encoding="utf-8",
    )
    return path


def test_data_split_filters_all_records_and_records_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = _manifest(tmp_path)
    documents, pages, nodes, queries = _records()

    result = apply_data_split(
        {"data_split": {"manifest": str(manifest), "name": "test"}},
        "demo",
        documents,
        pages,
        nodes,
        queries,
    )
    split_documents, split_pages, split_nodes, split_queries, info, copied_manifest = result

    assert [item.doc_id for item in split_documents] == ["doc_test"]
    assert [item.doc_id for item in split_pages] == ["doc_test"]
    assert [item.doc_id for item in split_nodes] == ["doc_test"]
    assert [item.doc_id for item in split_queries] == ["doc_test"]
    assert info is not None and info["name"] == "test" and info["query_count"] == 1
    assert copied_manifest == manifest


def test_test_split_must_be_marked_frozen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = _manifest(tmp_path)
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("test_status: frozen", "test_status: draft"), encoding="utf-8")
    documents, pages, nodes, queries = _records()

    with pytest.raises(ValueError, match="not marked as frozen"):
        apply_data_split(
            {"data_split": {"manifest": str(manifest), "name": "test"}},
            "demo",
            documents,
            pages,
            nodes,
            queries,
        )


def test_evaluation_loads_only_the_split_queries(tmp_path, monkeypatch):
    monkeypatch.setenv("MMDOC_RAG_DATA_ROOT", str(tmp_path / "data"))
    manifest = _manifest(tmp_path)
    documents, pages, nodes, queries = _records()
    write_processed_dataset(tmp_path / "data" / "processed" / "demo", documents, pages, nodes, queries)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "data_split.yaml").write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")

    selected = load_run_queries(
        run_dir,
        {"dataset": "demo", "data_split": {"name": "test"}},
    )

    assert [query.query_id for query in selected] == ["q_doc_test"]
