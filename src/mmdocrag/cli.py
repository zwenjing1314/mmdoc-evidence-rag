from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from mmdocrag.datasets import build_cn_annotations, prepare_dataset
from mmdocrag.evaluation import evaluate_run
from mmdocrag.exporting import export_demo_table
from mmdocrag.paths import resolve_project_path
from mmdocrag.retrieval import run_retrieval

app = typer.Typer(help="Multi-modal document evidence retrieval experiments.")
console = Console()


@app.command()
def prepare(
    dataset: Annotated[
        str, typer.Option(help="Dataset name: demo, mmdocir, cn_annual_reports.")
    ] = "demo",
    limit_docs: Annotated[
        int | None, typer.Option(help="Optional document limit for quick experiments.")
    ] = None,
) -> None:
    """Prepare raw data into standard parquet tables."""
    result = prepare_dataset(dataset, limit_docs=limit_docs)
    table = Table(title="Prepare Result")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("dataset", result.dataset)
    table.add_row("processed_dir", str(result.processed_dir))
    table.add_row("documents", str(result.documents))
    table.add_row("pages", str(result.pages))
    table.add_row("nodes", str(result.nodes))
    table.add_row("queries", str(result.queries))
    table.add_row("message", result.message)
    console.print(table)
    if result.documents == 0:
        console.print("[yellow]No usable data was prepared. For a smoke test, run:[/yellow]")
        console.print("[bold]uv run mdr prepare --dataset demo[/bold]")


@app.command("build-cn-annotations")
def build_cn_annotations_command(
    questions_per_doc: Annotated[
        int, typer.Option(help="Target QA rows per annual report.")
    ] = 8,
    limit_docs: Annotated[
        int | None, typer.Option(help="Optional PDF limit for quick annotation generation.")
    ] = None,
) -> None:
    """Build V2 Chinese annual report QA annotations from local PDFs."""
    output = build_cn_annotations(questions_per_doc=questions_per_doc, limit_docs=limit_docs)
    console.print(f"[green]Chinese annual report V2 annotations written to:[/green] {output}")


@app.command()
def retrieve(
    config: Annotated[Path, typer.Option(help="Experiment config path.")] = ...,
) -> None:
    """Run retrieval for an experiment config."""
    config_path = resolve_project_path(config)
    try:
        run_dir = run_retrieval(config_path)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("[yellow]If raw data is not ready, run the demo flow first:[/yellow]")
        console.print("[bold]uv run mdr prepare --dataset demo[/bold]")
        console.print("[bold]uv run mdr retrieve --config configs/experiments/demo_bm25_page.yaml[/bold]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Retrieval run written to:[/green] {run_dir}")


@app.command()
def evaluate(
    run: Annotated[
        Path, typer.Option(help="Run directory, for example runs/retrieval/demo_bm25_page/latest.")
    ] = ...,
) -> None:
    """Evaluate a retrieval run."""
    run_path = resolve_project_path(run)
    metrics = evaluate_run(run_path)
    table = Table(title="Evaluation Metrics")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for key, value in metrics.items():
        table.add_row(key, f"{value:.4f}")
    console.print(table)


@app.command("export-demo")
def export_demo(
    run: Annotated[Path, typer.Option(help="Evaluated run directory.")] = ...,
) -> None:
    """Export an opening-defense-ready markdown result table."""
    output = export_demo_table(resolve_project_path(run))
    console.print(f"[green]Opening experiment table written to:[/green] {output}")
