from __future__ import annotations

from mmdocrag.datasets import prepare_dataset
from mmdocrag.evaluation import evaluate_run
from mmdocrag.exporting import export_demo_table
from mmdocrag.retrieval import run_retrieval


def test_demo_full_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("MMDOC_RAG_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("MMDOC_RAG_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("MMDOC_RAG_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    result = prepare_dataset("demo")
    assert result.documents > 0
    assert result.queries > 0

    config = tmp_path / "demo_bm25.yaml"
    config.write_text(
        """
experiment_name: demo_bm25_page
dataset: demo
retriever:
  type: bm25_page
  top_k: [1, 5, 10]
output_dir: runs/retrieval/demo_bm25_page
""".strip(),
        encoding="utf-8",
    )

    run_dir = run_retrieval(config)
    metrics = evaluate_run(run_dir)
    output = export_demo_table(run_dir)

    assert metrics["page_recall@1"] > 0
    assert (run_dir / "predictions.parquet").exists()
    assert (run_dir / "summary.md").exists()
    assert output.exists()
