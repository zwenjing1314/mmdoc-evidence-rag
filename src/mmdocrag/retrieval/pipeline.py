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

SEARCH_SCOPE_CORPUS = "corpus"
SEARCH_SCOPE_DOCUMENT = "document"


def run_retrieval(config_path: Path) -> Path:
    config = load_config(config_path)
    dataset = str(config["dataset"])
    retriever = config.get("retriever", {})
    retriever_type = str(retriever.get("type", "bm25_page"))
    experiment_name = str(config.get("experiment_name", f"{dataset}_{retriever_type}"))
    processed_dir = data_root() / "processed" / dataset
    _, pages, nodes, queries = read_processed_dataset(processed_dir)  # 读取数据
    output_root = resolve_project_path(
        config.get("output_dir", f"runs/retrieval/{experiment_name}")
    )  # 输出目录
    run_dir = output_root / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )  # 根据时间创建新文件夹放到 output_root 文件夹下
    run_dir.mkdir(parents=True, exist_ok=True)
    search_scope = normalize_search_scope(retriever)

    if retriever_type == "bm25_page":
        hits = retrieve_pages(
            queries, pages, method="bm25", top_k=max_top_k(retriever), search_scope=search_scope
        )
    elif retriever_type == "dense_page":
        hits = retrieve_pages(
            queries,
            pages,
            method="dense",
            top_k=max_top_k(retriever),
            encoder=str(retriever.get("encoder", "BAAI/bge-m3")),
            search_scope=search_scope,
        )
    elif retriever_type == "layout_node":
        node_types = set(retriever.get("node_types", []))
        selected_nodes = [node for node in nodes if not node_types or node.node_type in node_types]
        hits = retrieve_nodes(
            queries,
            selected_nodes,
            method="dense",
            top_k=max_top_k(retriever),
            search_scope=search_scope,
        )
    elif retriever_type == "page_region":
        hits = retrieve_page_region(queries, pages, nodes, retriever)
    elif retriever_type == "global_region":
        hits = retrieve_global_region(queries, nodes, retriever)
    elif retriever_type == "oracle_page_region":
        hits = retrieve_oracle_page_region(queries, nodes, retriever)
    else:
        raise ValueError(f"Unsupported retriever type: {retriever_type}")

    write_hits(run_dir / "predictions.parquet", hits)
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
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


# 返回yaml文件中top_k中最大值
def max_top_k(retriever: dict[str, Any]) -> int:
    value = retriever.get("top_k", 10)
    if isinstance(value, list):
        return max(int(item) for item in value)
    return int(value)


# 判断是进行 全库检索 还是 单文档检索
def normalize_search_scope(retriever: dict[str, Any]) -> str:
    scope = str(retriever.get("search_scope", retriever.get("scope", SEARCH_SCOPE_CORPUS))).lower()
    if scope in {"doc", "same_doc", "in_document", SEARCH_SCOPE_DOCUMENT}:
        return SEARCH_SCOPE_DOCUMENT
    if scope in {"all", "global", SEARCH_SCOPE_CORPUS}:
        return SEARCH_SCOPE_CORPUS
    raise ValueError(f"Unsupported search_scope: {scope}. Use 'corpus' or 'document'.")


# # 为 单文档检索 的QueryRecord建立字典
def group_queries_by_doc(queries: list[QueryRecord]) -> dict[str, list[QueryRecord]]:
    grouped: dict[str, list[QueryRecord]] = {}
    for query in queries:
        grouped.setdefault(query.doc_id, []).append(query)
    return grouped


# 为 单文档检索 的PageRecord建立字典
def group_pages_by_doc(pages: list[PageRecord]) -> dict[str, list[PageRecord]]:
    grouped: dict[str, list[PageRecord]] = {}
    for page in pages:
        grouped.setdefault(page.doc_id, []).append(page)
    return grouped


def group_nodes_by_doc(nodes: list[EvidenceNode]) -> dict[str, list[EvidenceNode]]:
    grouped: dict[str, list[EvidenceNode]] = {}
    for node in nodes:
        grouped.setdefault(node.doc_id, []).append(node)
    return grouped


def group_nodes_by_page(nodes: list[EvidenceNode]) -> dict[str, list[EvidenceNode]]:
    grouped: dict[str, list[EvidenceNode]] = {}
    for node in nodes:
        grouped.setdefault(node.page_id, []).append(node)
    return grouped


def selected_node_types(retriever: dict[str, Any]) -> set[str]:
    return {str(item) for item in retriever.get("node_types", [])}


def filter_nodes_by_type(
    nodes: list[EvidenceNode], node_types: set[str] | None = None
) -> list[EvidenceNode]:
    if not node_types:
        return nodes
    return [node for node in nodes if node.node_type in node_types]


# 根据问题（Query）在页面（Pages）中进行检索、打分，并返回相关性最高的 Top-K 个结果
"""
可以把这个过程拆解为三个关键步骤：

1. 确定检索范围（隔离策略）
    全局模式 (SEARCH_SCOPE_CORPUS)：直接把所有传入的 pages 当作一个大的“题库”，每个问题都会和所有页面进行比对。
    文档内模式 (SEARCH_SCOPE_DOCUMENT)：利用你刚才提到的递归逻辑，先把问题和页面按文档分组。比如“万科”的问题只会在“万科”的页面里找答案，实现物理隔离。
2. 计算相关性分数（打分引擎）
    代码第 146 行：scores_by_query = score_texts(...)
    它会调用我们之前讨论过的 score_texts 函数。
    根据你配置的 method（如 bm25 或 dense），它会计算出一个分数矩阵。
        例如：问题 A 对 页面 1 得 0.9 分，对 页面 2 得 0.2 分...
3. 排序与截取（Top-K 选择）
    排序：把某个问题对所有页面的打分从高到低排列。
    截取：只拿走前 top_k 个分数最高的页面索引。
    封装：最后把这些高分页面包装成 RetrievalHit 对象（包含页码、分数、文本内容等）返回给你。
"""


def retrieve_pages(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    method: str,
    top_k: int,
    encoder: str | None = None,
    search_scope: str = SEARCH_SCOPE_CORPUS,
) -> list[RetrievalHit]:
    search_scope = normalize_search_scope({"search_scope": search_scope})
    if search_scope == SEARCH_SCOPE_DOCUMENT:
        pages_by_doc = group_pages_by_doc(pages)
        hits: list[RetrievalHit] = []
        for doc_id, doc_queries in group_queries_by_doc(queries).items():
            hits.extend(
                retrieve_pages(doc_queries, pages_by_doc.get(doc_id, []), method, top_k, encoder)
            )
        return hits

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
    encoder: str | None = None,
    search_scope: str = SEARCH_SCOPE_CORPUS,
) -> list[RetrievalHit]:
    search_scope = normalize_search_scope({"search_scope": search_scope})
    if search_scope == SEARCH_SCOPE_DOCUMENT:
        nodes_by_doc = group_nodes_by_doc(nodes)
        hits: list[RetrievalHit] = []
        for doc_id, doc_queries in group_queries_by_doc(queries).items():
            hits.extend(
                retrieve_nodes(doc_queries, nodes_by_doc.get(doc_id, []), method, top_k, encoder)
            )
        return hits

    docs = [node.text or node.node_id for node in nodes]
    scores_by_query = score_texts([query.question for query in queries], docs, method, encoder)
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
    search_scope = normalize_search_scope(retriever)
    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    region_method = str(retriever.get("region_method", retriever.get("method", "dense")))
    node_types = selected_node_types(retriever)
    page_hits = retrieve_pages(
        queries, pages, method="dense", top_k=page_top_k, encoder=encoder, search_scope=search_scope
    )
    nodes_by_page = group_nodes_by_page(filter_nodes_by_type(nodes, node_types))
    final_hits: list[RetrievalHit] = []
    for query in queries:
        query_page_hits = [hit for hit in page_hits if hit.query_id == query.query_id]
        candidate_nodes = []
        for hit in query_page_hits:
            candidate_nodes.extend(nodes_by_page.get(hit.page_id, []))
        if not candidate_nodes:
            continue
        node_hits = retrieve_nodes(
            [query],
            candidate_nodes,
            method=region_method,
            top_k=len(candidate_nodes),
            encoder=encoder,
        )
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
            final_hits.append(
                hit.model_copy(
                    update={"rank": rank, "score": float(score), "retriever": "page_region"}
                )
            )
    return final_hits


def retrieve_global_region(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    top_k = int(retriever.get("region_top_k", max_top_k(retriever)))
    method = str(retriever.get("method", retriever.get("region_method", "dense")))
    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    search_scope = normalize_search_scope(retriever)
    selected_nodes = filter_nodes_by_type(nodes, selected_node_types(retriever))
    hits = retrieve_nodes(
        queries,
        selected_nodes,
        method=method,
        top_k=top_k,
        encoder=encoder,
        search_scope=search_scope,
    )
    return [hit.model_copy(update={"retriever": "global_region"}) for hit in hits]


def retrieve_oracle_page_region(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    region_top_k = int(retriever.get("region_top_k", max_top_k(retriever)))
    method = str(retriever.get("method", retriever.get("region_method", "dense")))
    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    nodes_by_page = group_nodes_by_page(filter_nodes_by_type(nodes, selected_node_types(retriever)))
    hits: list[RetrievalHit] = []
    for query in queries:
        candidate_nodes: list[EvidenceNode] = []
        for page_id in query.evidence_page_ids:
            candidate_nodes.extend(nodes_by_page.get(page_id, []))
        if not candidate_nodes:
            continue
        query_hits = retrieve_nodes(
            [query],
            candidate_nodes,
            method=method,
            top_k=region_top_k,
            encoder=encoder,
        )
        hits.extend(
            hit.model_copy(update={"retriever": "oracle_page_region"}) for hit in query_hits
        )
    return hits


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
