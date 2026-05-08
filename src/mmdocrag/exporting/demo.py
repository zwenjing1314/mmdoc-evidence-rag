from __future__ import annotations

import json
from pathlib import Path

from mmdocrag.paths import artifacts_root


def export_demo_table(run: Path) -> Path:
    run_dir = run.resolve() if run.is_symlink() else run
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Evaluate the run before exporting demo table: {metrics_path}")
    run_info = json.loads((run_dir / "run_info.json").read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    output = artifacts_root() / "figures" / "opening_experiment_table.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Opening Defense Retrieval Result",
        "",
        "| Dataset | Method | Page Recall@1 | Page Recall@5 | MRR | nDCG@5 | Region Hit@5 |",
        "|---|---|---:|---:|---:|---:|---:|",
        (
            f"| {run_info['dataset']} | {run_info['retriever_type']} | "
            f"{metrics.get('page_recall@1', 0):.4f} | "
            f"{metrics.get('page_recall@5', 0):.4f} | "
            f"{metrics.get('mrr', 0):.4f} | "
            f"{metrics.get('ndcg@5', 0):.4f} | "
            f"{metrics.get('region_hit@5', 0):.4f} |"
        ),
        "",
        f"Source run: `{run_dir}`",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
