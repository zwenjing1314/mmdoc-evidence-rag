from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
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
_SENTENCE_TRANSFORMER_CACHE: dict[str, Any] = {}


@dataclass(frozen=True)
class ScoreResult:
    scores: list[list[float]]
    backend: str


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
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
        )
    elif retriever_type == "hybrid_page":
        hits = retrieve_hybrid_pages(queries, pages, retriever)
    elif retriever_type == "layout_node":
        node_types = set(retriever.get("node_types", []))
        selected_nodes = [node for node in nodes if not node_types or node.node_type in node_types]
        hits = retrieve_nodes(
            queries,
            selected_nodes,
            method="dense",
            top_k=max_top_k(retriever),
            search_scope=search_scope,
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
        )
    elif retriever_type == "page_region":
        hits = retrieve_page_region(queries, pages, nodes, retriever)
    elif retriever_type == "hybrid_page_region":
        hits = retrieve_hybrid_page_region(queries, pages, nodes, retriever)
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
                "actual_retrievers": sorted({hit.retriever for hit in hits}),
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


def require_dense_model(retriever: dict[str, Any]) -> bool:
    return bool(retriever.get("require_model", retriever.get("require_dense_model", False)))


def dense_batch_size(retriever: dict[str, Any]) -> int:
    return int(retriever.get("dense_batch_size", os.getenv("MDR_DENSE_BATCH_SIZE", 8)))


def dense_max_seq_length(retriever: dict[str, Any]) -> int | None:
    value = retriever.get("dense_max_seq_length", os.getenv("MDR_DENSE_MAX_SEQ_LENGTH"))
    if value in {None, ""}:
        return None
    return int(value)


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


def page_fusion_methods(retriever: dict[str, Any]) -> list[str]:
    methods = retriever.get("page_methods", retriever.get("methods", ["bm25", "dense"]))
    if isinstance(methods, str):
        return [methods]
    return [str(method) for method in methods]


def normalize_retrieval_method(value: Any, default: str = "dense") -> str:
    method = str(value or default).lower()
    aliases = {
        "bm25_page": "bm25",
        "dense_page": "dense",
        "tfidf_page": "tfidf",
        "layout_node": "dense",
        "dense_node": "dense",
        "bm25_node": "bm25",
        "tfidf_node": "tfidf",
    }
    return aliases.get(method, method)


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
    require_dense_model: bool = False,
    dense_batch_size: int = 8,
    dense_max_seq_length: int | None = None,
) -> list[RetrievalHit]:
    search_scope = normalize_search_scope({"search_scope": search_scope})
    if search_scope == SEARCH_SCOPE_DOCUMENT:
        pages_by_doc = group_pages_by_doc(pages)
        hits: list[RetrievalHit] = []
        for doc_id, doc_queries in group_queries_by_doc(queries).items():
            hits.extend(
                retrieve_pages(
                    doc_queries,
                    pages_by_doc.get(doc_id, []),
                    method,
                    top_k,
                    encoder,
                    require_dense_model=require_dense_model,
                    dense_batch_size=dense_batch_size,
                    dense_max_seq_length=dense_max_seq_length,
                )
            )
        return hits

    docs = [page.page_text or page.ocr_text or page.page_id for page in pages]
    score_result = score_texts_with_backend(
        [query.question for query in queries],
        docs,
        method,
        encoder,
        require_dense_model,
        dense_batch_size,
        dense_max_seq_length,
    )
    hits: list[RetrievalHit] = []
    for query, scores in zip(queries, score_result.scores, strict=True):
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
                    retriever=score_result.backend,
                )
            )
    return hits


def retrieve_hybrid_pages(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    top_k = int(retriever.get("page_top_k", max_top_k(retriever)))
    candidate_top_k = int(retriever.get("candidate_top_k", max(top_k, 20)))
    search_scope = normalize_search_scope(retriever)
    if search_scope == SEARCH_SCOPE_DOCUMENT:
        pages_by_doc = group_pages_by_doc(pages)
        hits: list[RetrievalHit] = []
        for doc_id, doc_queries in group_queries_by_doc(queries).items():
            hits.extend(
                retrieve_hybrid_pages(
                    doc_queries,
                    pages_by_doc.get(doc_id, []),
                    {**retriever, "search_scope": SEARCH_SCOPE_CORPUS},
                )
            )
        return hits

    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    method_hits = [
        retrieve_pages(
            queries,
            pages,
            method=method,
            top_k=candidate_top_k,
            encoder=encoder,
            search_scope=SEARCH_SCOPE_CORPUS,
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
        )
        for method in page_fusion_methods(retriever)
    ]
    page_by_id = {page.page_id: page for page in pages}
    final_hits: list[RetrievalHit] = []
    for query in queries:
        rankings = [
            [hit.page_id for hit in hits if hit.query_id == query.query_id] for hits in method_hits
        ]
        fused = reciprocal_rank_fusion([ranking for ranking in rankings if ranking])
        ranked_page_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
        for rank, page_id in enumerate(ranked_page_ids, start=1):
            page = page_by_id[page_id]
            final_hits.append(
                RetrievalHit(
                    query_id=query.query_id,
                    rank=rank,
                    score=float(fused[page_id]),
                    doc_id=page.doc_id,
                    page_id=page.page_id,
                    text=page.page_text or page.ocr_text,
                    retriever="hybrid_page",
                )
            )
    return final_hits


def retrieve_nodes(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    method: str,
    top_k: int,
    encoder: str | None = None,
    search_scope: str = SEARCH_SCOPE_CORPUS,
    require_dense_model: bool = False,
    dense_batch_size: int = 8,
    dense_max_seq_length: int | None = None,
) -> list[RetrievalHit]:
    search_scope = normalize_search_scope({"search_scope": search_scope})
    if search_scope == SEARCH_SCOPE_DOCUMENT:
        nodes_by_doc = group_nodes_by_doc(nodes)
        hits: list[RetrievalHit] = []
        for doc_id, doc_queries in group_queries_by_doc(queries).items():
            hits.extend(
                retrieve_nodes(
                    doc_queries,
                    nodes_by_doc.get(doc_id, []),
                    method,
                    top_k,
                    encoder,
                    require_dense_model=require_dense_model,
                    dense_batch_size=dense_batch_size,
                    dense_max_seq_length=dense_max_seq_length,
                )
            )
        return hits

    docs = [node.text or node.node_id for node in nodes]
    score_result = score_texts_with_backend(
        [query.question for query in queries],
        docs,
        method,
        encoder,
        require_dense_model,
        dense_batch_size,
        dense_max_seq_length,
    )
    hits: list[RetrievalHit] = []
    for query, scores in zip(queries, score_result.scores, strict=True):
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
                    retriever=score_result.backend,
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
    page_method = normalize_retrieval_method(retriever.get("page_retriever"), "dense")
    region_method = normalize_retrieval_method(
        retriever.get("region_method", retriever.get("region_retriever", retriever.get("method"))),
        "dense",
    )
    page_hits = retrieve_pages(
        queries,
        pages,
        method=page_method,
        top_k=page_top_k,
        encoder=encoder,
        search_scope=search_scope,
        require_dense_model=require_dense_model(retriever),
        dense_batch_size=dense_batch_size(retriever),
        dense_max_seq_length=dense_max_seq_length(retriever),
    )
    return retrieve_regions_from_page_hits(
        queries,
        page_hits,
        nodes,
        retriever,
        region_top_k=region_top_k,
        region_method=region_method,
        encoder=encoder,
        retriever_name="page_region",
    )


def retrieve_hybrid_page_region(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    region_top_k = int(retriever.get("region_top_k", 5))
    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    region_method = normalize_retrieval_method(
        retriever.get("region_method", retriever.get("region_retriever", retriever.get("method"))),
        "dense",
    )
    page_hits = retrieve_hybrid_pages(queries, pages, retriever)
    return retrieve_regions_from_page_hits(
        queries,
        page_hits,
        nodes,
        retriever,
        region_top_k=region_top_k,
        region_method=region_method,
        encoder=encoder,
        retriever_name="hybrid_page_region",
    )


def retrieve_regions_from_page_hits(
    queries: list[QueryRecord],
    page_hits: list[RetrievalHit],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
    region_top_k: int,
    region_method: str,
    encoder: str,
    retriever_name: str,
) -> list[RetrievalHit]:
    node_types = selected_node_types(retriever)
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
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
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
                    update={"rank": rank, "score": float(score), "retriever": retriever_name}
                )
            )
    return final_hits


def retrieve_global_region(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    top_k = int(retriever.get("region_top_k", max_top_k(retriever)))
    method = normalize_retrieval_method(
        retriever.get("method", retriever.get("region_method", retriever.get("region_retriever"))),
        "dense",
    )
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
        require_dense_model=require_dense_model(retriever),
        dense_batch_size=dense_batch_size(retriever),
        dense_max_seq_length=dense_max_seq_length(retriever),
    )
    return [hit.model_copy(update={"retriever": "global_region"}) for hit in hits]


def retrieve_oracle_page_region(
    queries: list[QueryRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    region_top_k = int(retriever.get("region_top_k", max_top_k(retriever)))
    method = normalize_retrieval_method(
        retriever.get("method", retriever.get("region_method", retriever.get("region_retriever"))),
        "dense",
    )
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
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
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
    return score_texts_with_backend(queries, docs, method, encoder).scores


def score_texts_with_backend(
    queries: list[str],
    docs: list[str],
    method: str,
    encoder: str | None = None,
    require_model: bool = False,
    batch_size: int = 8,
    max_seq_length: int | None = None,
) -> ScoreResult:
    if method == "bm25":
        bm25 = SimpleBM25(docs)
        return ScoreResult([bm25.score(query) for query in queries], "bm25")
    if method == "dense":
        model_scores = try_sentence_transformer_scores(
            queries, docs, encoder, batch_size=batch_size, max_seq_length=max_seq_length
        )
        if model_scores is not None:
            return model_scores
        if require_model:
            model_name = encoder or "BAAI/bge-m3"
            raise RuntimeError(
                f"Dense retrieval requires local SentenceTransformer model `{model_name}`, "
                "but it could not be loaded. Download/cache the model first, or set "
                "`require_model: false` to allow TF-IDF fallback."
            )
        tfidf = SimpleTfidf(docs)
        return ScoreResult([tfidf.score(query) for query in queries], "dense:tfidf_fallback")
    tfidf = SimpleTfidf(docs)
    return ScoreResult([tfidf.score(query) for query in queries], "tfidf")


def try_sentence_transformer_scores(
    queries: list[str],
    docs: list[str],
    encoder: str | None,
    batch_size: int = 8,
    max_seq_length: int | None = None,
) -> ScoreResult | None:
    if os.getenv("MDR_DISABLE_SENTENCE_TRANSFORMERS", "0") == "1":
        return None
    try:
        from sentence_transformers.util import cos_sim

        model_name = encoder or "BAAI/bge-m3"
        model = get_sentence_transformer(model_name, max_seq_length=max_seq_length)
        query_embeddings = model.encode(
            queries, normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False
        )
        doc_embeddings = model.encode(
            docs, normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False
        )
        matrix = cos_sim(query_embeddings, doc_embeddings).cpu().numpy()
        scores = [[float(value) for value in row] for row in matrix]
        suffix = f":maxlen={max_seq_length}" if max_seq_length else ""
        return ScoreResult(scores, f"dense:sentence_transformers:{model_name}{suffix}")
    except Exception:
        return None


def get_sentence_transformer(model_name: str, max_seq_length: int | None = None) -> Any:
    cache_key = f"{model_name}::max_seq_length={max_seq_length or 'default'}"
    if cache_key in _SENTENCE_TRANSFORMER_CACHE:
        return _SENTENCE_TRANSFORMER_CACHE[cache_key]

    from sentence_transformers import SentenceTransformer

    previous_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    previous_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    if os.getenv("MDR_ALLOW_MODEL_DOWNLOAD", "0") != "1":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    try:
        try:
            model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            if os.getenv("MDR_ALLOW_MODEL_DOWNLOAD", "0") != "1":
                raise
            model = SentenceTransformer(model_name)
    finally:
        if previous_hf_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous_hf_offline
        if previous_transformers_offline is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = previous_transformers_offline

    if max_seq_length:
        model.max_seq_length = max_seq_length

    _SENTENCE_TRANSFORMER_CACHE[cache_key] = model
    return model


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
