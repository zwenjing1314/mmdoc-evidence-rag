from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from mmdocrag.config import load_config
from mmdocrag.io import read_processed_dataset, write_hits
from mmdocrag.paths import data_root, resolve_project_path
from mmdocrag.retrieval.scoring import SimpleBM25, SimpleTfidf, reciprocal_rank_fusion
from mmdocrag.schemas import EvidenceNode, PageRecord, QueryRecord, RetrievalHit


def run_retrieval(config_path: Path) -> Path:
    config = load_config(config_path)
    dataset = str(config["dataset"])
    retriever = config.get("retriever", {})
    retriever_type = str(retriever.get("type", "bm25_page"))
    experiment_name = str(config.get("experiment_name", f"{dataset}_{retriever_type}"))
    processed_dir = data_root() / "processed" / dataset
    _, pages, nodes, queries = read_processed_dataset(processed_dir)
    output_root = resolve_project_path(config.get("output_dir", f"runs/retrieval/{experiment_name}"))
    run_dir = output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    if retriever_type == "bm25_page":
        hits = retrieve_pages(queries, pages, method="bm25", top_k=max_top_k(retriever))
    elif retriever_type == "dense_page":
        hits = retrieve_pages(
            queries,
            pages,
            method="dense",
            top_k=max_top_k(retriever),
            encoder=str(retriever.get("encoder", "BAAI/bge-m3")),
        )
    elif retriever_type == "layout_node":
        node_types = set(retriever.get("node_types", []))
        selected_nodes = [node for node in nodes if not node_types or node.node_type in node_types]
        hits = retrieve_nodes(queries, selected_nodes, method="dense", top_k=max_top_k(retriever))
    elif retriever_type == "page_region":
        hits = retrieve_page_region(queries, pages, nodes, retriever)
    else:
        raise ValueError(f"Unsupported retriever type: {retriever_type}")

    write_hits(run_dir / "predictions.parquet", hits)
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "run_info.json").write_text(
        json.dumps(
            {
                "experiment_name": experiment_name,
                "dataset": dataset,
                "retriever_type": retriever_type,
                "hits": len(hits),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    update_latest(output_root, run_dir)
    return run_dir


def max_top_k(retriever: dict[str, Any]) -> int:
    value = retriever.get("top_k", 10)
    if isinstance(value, list):
        return max(int(item) for item in value)
    return int(value)


def retrieve_pages(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    method: str,
    top_k: int,
    encoder: str | None = None,
) -> list[RetrievalHit]:
    docs = [page.page_text or page.ocr_text or page.page_id for page in pages]
    scores_by_query = score_texts([query.question for query in queries], docs, method, encoder)
    hits: list[RetrievalHit] = []
    for query, scores in zip(queries, scores_by_query, strict=True):
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        for rank, (index, score) in enumerate(ranked, start=1):
            page = pages[index]
            hits.append(
                RetrievalHit(
                    query_id=query.query_id,
                    rank=rank,
                    score=float(score),
                    doc_id=page.doc_id,
                    page_id=page.page_id,
                    text=page.page_text or page.ocr_text,
                    retriever=method,
                )
            )
    return hits


def retrieve_nodes(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    method: str,
    top_k: int,
) -> list[RetrievalHit]:
    docs = [node.text or node.node_id for node in nodes]
    scores_by_query = score_texts([query.question for query in queries], docs, method)
    hits: list[RetrievalHit] = []
    for query, scores in zip(queries, scores_by_query, strict=True):
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        for rank, (index, score) in enumerate(ranked, start=1):
            node = nodes[index]
            hits.append(
                RetrievalHit(
                    query_id=query.query_id,
                    rank=rank,
                    score=float(score),
                    doc_id=node.doc_id,
                    page_id=node.page_id,
                    node_id=node.node_id,
                    node_type=node.node_type,
                    text=node.text,
                    retriever=method,
                )
            )
    return hits


def retrieve_page_region(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    page_top_k = int(retriever.get("page_top_k", 10))
    region_top_k = int(retriever.get("region_top_k", 5))
    page_hits = retrieve_pages(queries, pages, method="dense", top_k=page_top_k)
    nodes_by_page: dict[str, list[EvidenceNode]] = {}
    for node in nodes:
        nodes_by_page.setdefault(node.page_id, []).append(node)
    final_hits: list[RetrievalHit] = []
    for query in queries:
        query_page_hits = [hit for hit in page_hits if hit.query_id == query.query_id]
        candidate_nodes = []
        for hit in query_page_hits:
            candidate_nodes.extend(nodes_by_page.get(hit.page_id, []))
        if not candidate_nodes:
            continue
        node_hits = retrieve_nodes([query], candidate_nodes, method="dense", top_k=len(candidate_nodes))
        page_ranking = [hit.page_id for hit in query_page_hits]
        node_ranking = [hit.node_id or "" for hit in node_hits]
        fused_pages = reciprocal_rank_fusion([page_ranking])
        fused_nodes = reciprocal_rank_fusion([node_ranking])
        rescored = []
        for hit in node_hits:
            node_score = fused_nodes.get(hit.node_id or "", 0.0)
            page_score = fused_pages.get(hit.page_id, 0.0)
            rescored.append((hit, node_score + page_score))
        for rank, (hit, score) in enumerate(
            sorted(rescored, key=lambda item: item[1], reverse=True)[:region_top_k], start=1
        ):
            final_hits.append(hit.model_copy(update={"rank": rank, "score": float(score), "retriever": "page_region"}))
    return final_hits


def score_texts(
    queries: list[str],
    docs: list[str],
    method: str,
    encoder: str | None = None,
) -> list[list[float]]:
    if method == "bm25":
        bm25 = SimpleBM25(docs)
        return [bm25.score(query) for query in queries]
    if method == "dense":
        model_scores = try_sentence_transformer_scores(queries, docs, encoder)
        if model_scores is not None:
            return model_scores
        tfidf = SimpleTfidf(docs)
        return [tfidf.score(query) for query in queries]
    tfidf = SimpleTfidf(docs)
    return [tfidf.score(query) for query in queries]


def try_sentence_transformer_scores(
    queries: list[str],
    docs: list[str],
    encoder: str | None,
) -> list[list[float]] | None:
    if os.getenv("MDR_DISABLE_SENTENCE_TRANSFORMERS", "0") == "1":
        return None
    try:
        from sentence_transformers import SentenceTransformer
        from sentence_transformers.util import cos_sim

        model_name = encoder or "BAAI/bge-m3"
        try:
            model = SentenceTransformer(model_name, local_files_only=True)
        except TypeError:
            if os.getenv("MDR_ALLOW_MODEL_DOWNLOAD", "0") != "1":
                return None
            model = SentenceTransformer(model_name)
        query_embeddings = model.encode(queries, normalize_embeddings=True)
        doc_embeddings = model.encode(docs, normalize_embeddings=True)
        matrix = cos_sim(query_embeddings, doc_embeddings).cpu().numpy()
        return [[float(value) for value in row] for row in matrix]
    except Exception:
        return None


def update_latest(output_root: Path, run_dir: Path) -> None:
    latest = output_root / "latest"
    try:
        if latest.is_symlink() or latest.exists():
            if latest.is_dir() and not latest.is_symlink():
                shutil.rmtree(latest)
            else:
                latest.unlink()
        latest.symlink_to(run_dir.name, target_is_directory=True)
    except OSError:
        (output_root / "latest.txt").write_text(str(run_dir), encoding="utf-8")
