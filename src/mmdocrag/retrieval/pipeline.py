from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
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
_ACTIVE_RETRIEVAL_STARTED_AT: float | None = None


def log_retrieval(message: str) -> None:
    """Print progress immediately so long-running CPU retrieval is observable."""
    if _ACTIVE_RETRIEVAL_STARTED_AT is None:
        print(f"[mdr] {message}", flush=True)
        return
    elapsed = time.monotonic() - _ACTIVE_RETRIEVAL_STARTED_AT
    print(
        f"[mdr] {message} | experiment_elapsed={elapsed:.1f}s ({format_elapsed(elapsed)})",
        flush=True,
    )


def format_elapsed(seconds: float) -> str:
    """Format an elapsed duration for quick reading in long terminal runs."""
    hours, remainder = divmod(max(0.0, seconds), 3600)
    minutes, seconds_remainder = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds_remainder:04.1f}"


def progress_interval(total: int) -> int:
    """Emit about 20 updates, while still reporting small experiments per document."""
    return max(1, min(10, total // 20))


def progress_timing(index: int, total: int, started_at: float) -> str:
    elapsed = time.monotonic() - started_at
    if index <= 1:
        return f"elapsed {elapsed:.1f}s; estimating remaining time after this document."
    average_per_document = elapsed / (index - 1)
    remaining = average_per_document * (total - index + 1)
    return f"elapsed {elapsed:.1f}s; estimated remaining {remaining:.1f}s."


def release_mps_cache() -> None:
    """Release temporary tensors between documents on memory-constrained Apple MPS."""
    try:
        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except (ImportError, AttributeError):
        return

METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "营业收入": ("营业收入", "营收"),
    "归母净利润": ("归属于上市公司股东的净利润", "归母净利润", "净利润"),
    "经营活动现金流量净额": ("经营活动产生的现金流量净额", "经营活动现金流量净额"),
    "研发投入": ("研发投入", "研发费用", "研发支出"),
    "资产总额": ("资产总额", "总资产"),
    "负债合计": ("负债合计", "负债总额"),
    "报告标题": ("报告标题", "标题处显示", "标题是什么"),
    "报告年度": ("报告年度", "对应的报告年度", "哪一年"),
    "风险": ("主要风险", "风险因素", "风险"),
    "同比变化": ("同比", "本年比上年增减", "增减幅度", "相比上年"),
}

UNIT_TERMS = (
    "人民币元",
    "人民币万元",
    "人民币亿元",
    "百分点",
    "万元",
    "亿元",
    "元",
    "%",
)

QUESTION_STOP_TERMS = {
    "多少",
    "是什么",
    "是多少",
    "披露",
    "显示",
    "首页",
    "标题处",
    "这份",
    "年度报告",
    "报告",
    "对应",
    "公司",
    "中",
    "的",
    "了",
    "和",
    "或",
}


@dataclass(frozen=True)
class ScoreResult:
    scores: list[list[float]]
    backend: str


@dataclass
class EvidenceCandidate:
    node: EvidenceNode
    from_page_candidate: bool = False
    from_global_region: bool = False
    from_structured_scan: bool = False
    from_cover_anchor: bool = False
    page_rank: int | None = None
    global_rank: int | None = None
    structured_rank: int | None = None
    cover_rank: int | None = None
    structured_score: float = 0.0
    semantic_rank: int | None = None
    semantic_score: float = 0.0
    coverage_slots: set[str] | None = None
    coverage_score: float = 0.0
    localization_score: float = 0.0
    combined_score: float = 0.0


def run_retrieval(config_path: Path, split_name: str | None = None) -> Path:
    global _ACTIVE_RETRIEVAL_STARTED_AT
    started_at = time.monotonic()
    _ACTIVE_RETRIEVAL_STARTED_AT = started_at
    config = load_config(config_path)
    dataset = str(config["dataset"])
    retriever = config.get("retriever", {})
    retriever_type = str(retriever.get("type", "bm25_page"))
    experiment_name = str(config.get("experiment_name", f"{dataset}_{retriever_type}"))
    processed_dir = data_root() / "processed" / dataset
    documents, pages, nodes, queries = read_processed_dataset(processed_dir)
    documents, pages, nodes, queries, split_info, split_manifest = apply_data_split(
        config, dataset, documents, pages, nodes, queries, split_name
    )
    output_root = resolve_project_path(
        config.get("output_dir", f"runs/retrieval/{experiment_name}")
    )  # 输出目录
    if split_info is not None:
        output_root = output_root / str(split_info["name"])
    run_dir = output_root / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )  # 根据时间创建新文件夹放到 output_root 文件夹下
    run_dir.mkdir(parents=True, exist_ok=True)
    search_scope = normalize_search_scope(retriever)
    log_retrieval(
        f"Starting {experiment_name}: {len(queries)} queries, {len(pages)} pages, "
        f"scope={search_scope}, retriever={retriever_type}."
    )

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
    elif retriever_type == "evidence_set_region":
        hits = retrieve_evidence_set_region(queries, pages, nodes, retriever)
    else:
        raise ValueError(f"Unsupported retriever type: {retriever_type}")

    log_retrieval(
        f"Retrieval finished: {len(hits)} hits generated in {time.monotonic() - started_at:.1f}s. "
        "Writing result files..."
    )

    write_hits(run_dir / "predictions.parquet", hits)
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if split_manifest is not None:
        shutil.copy2(split_manifest, run_dir / "data_split.yaml")
    (run_dir / "run_info.json").write_text(
        json.dumps(
            {
                "experiment_name": experiment_name,
                "dataset": dataset,
                "retriever_type": retriever_type,
                "hits": len(hits),
                "actual_retrievers": sorted({hit.retriever for hit in hits}),
                "data_split": split_info,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    update_latest(output_root, run_dir)
    log_retrieval(f"Results are ready in {run_dir}.")
    _ACTIVE_RETRIEVAL_STARTED_AT = None
    return run_dir


def apply_data_split(
    config: dict[str, Any],
    dataset: str,
    documents: list[Any],
    pages: list[PageRecord],
    nodes: list[EvidenceNode],
    queries: list[QueryRecord],
    split_override: str | None = None,
) -> tuple[
    list[Any], list[PageRecord], list[EvidenceNode], list[QueryRecord], dict[str, Any] | None, Path | None
]:
    """Filter a processed dataset by the immutable document-level split manifest."""
    split_config = config.get("data_split")
    if not split_config:
        if split_override is not None:
            raise ValueError("`--split` requires a `data_split.manifest` in the experiment config.")
        return documents, pages, nodes, queries, None, None

    manifest_value = split_config.get("manifest")
    if not manifest_value:
        raise ValueError("`data_split.manifest` is required when data_split is configured.")
    manifest_path = resolve_project_path(manifest_value)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing data split manifest: {manifest_path}")
    manifest = load_config(manifest_path)
    if str(manifest.get("dataset", "")) != dataset:
        raise ValueError(
            f"Split manifest dataset `{manifest.get('dataset')}` does not match experiment dataset `{dataset}`."
        )
    qa_source = manifest.get("qa_source")
    qa_source_hash = manifest.get("qa_source_sha256")
    if qa_source and qa_source_hash:
        qa_source_path = resolve_project_path(str(qa_source))
        if not qa_source_path.exists():
            raise FileNotFoundError(f"Missing frozen QA source: {qa_source_path}")
        actual_qa_hash = sha256(qa_source_path.read_bytes()).hexdigest()
        if actual_qa_hash != str(qa_source_hash):
            raise ValueError(
                "Frozen QA source hash does not match the split manifest. "
                "Do not run paper experiments until the data version is resolved."
            )

    split_name = str(split_override or split_config.get("name", "test"))
    splits = manifest.get("splits")
    if not isinstance(splits, dict) or split_name not in splits:
        available = ", ".join(sorted(splits)) if isinstance(splits, dict) else "none"
        raise ValueError(f"Unknown data split `{split_name}`. Available splits: {available}.")
    if split_name == "test" and manifest.get("test_status") != "frozen":
        raise ValueError("The requested test split is not marked as frozen in its manifest.")

    split_docs = {name: [str(doc_id) for doc_id in doc_ids] for name, doc_ids in splits.items()}
    declared_doc_ids = [doc_id for doc_ids in split_docs.values() for doc_id in doc_ids]
    if len(declared_doc_ids) != len(set(declared_doc_ids)):
        raise ValueError("A document appears in more than one split.")
    available_doc_ids = {document.doc_id for document in documents}
    if set(declared_doc_ids) != available_doc_ids:
        missing = sorted(available_doc_ids - set(declared_doc_ids))
        unknown = sorted(set(declared_doc_ids) - available_doc_ids)
        raise ValueError(f"Split manifest does not match processed documents. Missing={missing}; unknown={unknown}.")

    selected_doc_ids = set(split_docs[split_name])
    filtered_documents = [document for document in documents if document.doc_id in selected_doc_ids]
    filtered_pages = [page for page in pages if page.doc_id in selected_doc_ids]
    filtered_nodes = [node for node in nodes if node.doc_id in selected_doc_ids]
    filtered_queries = [query for query in queries if query.doc_id in selected_doc_ids]
    if not filtered_queries:
        raise ValueError(f"Data split `{split_name}` contains no queries.")

    manifest_hash = sha256(manifest_path.read_bytes()).hexdigest()
    project_path = resolve_project_path(".")
    try:
        manifest_reference = str(manifest_path.relative_to(project_path))
    except ValueError:
        manifest_reference = str(manifest_path)
    split_info = {
        "name": split_name,
        "manifest": manifest_reference,
        "manifest_sha256": manifest_hash,
        "test_status": manifest.get("test_status"),
        "qa_source": qa_source,
        "qa_source_sha256": qa_source_hash,
        "document_count": len(filtered_documents),
        "page_count": len(filtered_pages),
        "node_count": len(filtered_nodes),
        "query_count": len(filtered_queries),
    }
    return filtered_documents, filtered_pages, filtered_nodes, filtered_queries, split_info, manifest_path


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
        queries_by_doc = group_queries_by_doc(queries)
        total_documents = len(queries_by_doc)
        started_at = time.monotonic()
        interval = progress_interval(total_documents)
        for index, (doc_id, doc_queries) in enumerate(queries_by_doc.items(), start=1):
            if method == "dense" and (index == 1 or index % interval == 0 or index == total_documents):
                log_retrieval(
                    f"Dense page retrieval: document {index}/{total_documents}; "
                    f"{len(doc_queries)} queries, {len(pages_by_doc.get(doc_id, []))} pages; "
                    f"{progress_timing(index, total_documents, started_at)}"
                )
            doc_hits = retrieve_pages(
                doc_queries,
                pages_by_doc.get(doc_id, []),
                method,
                top_k,
                encoder,
                require_dense_model=require_dense_model,
                dense_batch_size=dense_batch_size,
                dense_max_seq_length=dense_max_seq_length,
            )
            hits.extend(doc_hits)
            if method == "dense":
                release_mps_cache()
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
        queries_by_doc = group_queries_by_doc(queries)
        total_documents = len(queries_by_doc)
        started_at = time.monotonic()
        interval = progress_interval(total_documents)
        for index, (doc_id, doc_queries) in enumerate(queries_by_doc.items(), start=1):
            if index == 1 or index % interval == 0 or index == total_documents:
                log_retrieval(
                    f"Hybrid page retrieval: document {index}/{total_documents}; "
                    f"{len(doc_queries)} queries, {len(pages_by_doc.get(doc_id, []))} pages; "
                    f"{progress_timing(index, total_documents, started_at)}"
                )
            doc_hits = retrieve_hybrid_pages(
                doc_queries,
                pages_by_doc.get(doc_id, []),
                {**retriever, "search_scope": SEARCH_SCOPE_CORPUS},
            )
            hits.extend(doc_hits)
            if "dense" in page_fusion_methods(retriever):
                release_mps_cache()
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
        queries_by_doc = group_queries_by_doc(queries)
        total_documents = len(queries_by_doc)
        started_at = time.monotonic()
        interval = progress_interval(total_documents)
        for index, (doc_id, doc_queries) in enumerate(queries_by_doc.items(), start=1):
            if method == "dense" and (index == 1 or index % interval == 0 or index == total_documents):
                log_retrieval(
                    f"Dense layout-node retrieval: document {index}/{total_documents}; "
                    f"{len(doc_queries)} queries, {len(nodes_by_doc.get(doc_id, []))} nodes; "
                    f"{progress_timing(index, total_documents, started_at)}"
                )
            doc_hits = retrieve_nodes(
                doc_queries,
                nodes_by_doc.get(doc_id, []),
                method,
                top_k,
                encoder,
                require_dense_model=require_dense_model,
                dense_batch_size=dense_batch_size,
                dense_max_seq_length=dense_max_seq_length,
            )
            hits.extend(doc_hits)
            if method == "dense":
                release_mps_cache()
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


def retrieve_evidence_set_region(
    queries: list[QueryRecord],
    pages: list[PageRecord],
    nodes: list[EvidenceNode],
    retriever: dict[str, Any],
) -> list[RetrievalHit]:
    page_top_k = int(retriever.get("page_top_k", 10))
    global_region_top_k = int(retriever.get("global_region_top_k", 20))
    structured_scan_top_k = int(retriever.get("structured_scan_top_k", 20))
    cover_anchor_top_k = int(retriever.get("cover_anchor_top_k", 8))
    output_top_k = int(retriever.get("output_top_k", retriever.get("region_top_k", 5)))
    max_evidence_nodes = int(retriever.get("max_evidence_nodes", 3))
    use_hybrid_page = bool(retriever.get("use_hybrid_page", True))
    use_global_region = bool(retriever.get("use_global_region", True))
    use_structured_scan = bool(retriever.get("use_structured_scan", True))
    use_cover_anchor = bool(retriever.get("use_cover_anchor", True))
    use_slot_coverage = bool(retriever.get("use_slot_coverage", True))
    selection_mode = str(retriever.get("selection_mode", "greedy"))
    if selection_mode not in {"greedy", "single_node"}:
        raise ValueError("selection_mode must be `greedy` or `single_node`.")
    encoder = str(retriever.get("encoder", "BAAI/bge-m3"))
    region_method = normalize_retrieval_method(
        retriever.get("region_method", retriever.get("method", retriever.get("region_retriever"))),
        "dense",
    )
    selected_nodes = filter_nodes_by_type(nodes, selected_node_types(retriever))
    nodes_by_page = group_nodes_by_page(selected_nodes)
    nodes_by_doc = group_nodes_by_doc(selected_nodes)
    nodes_by_id = {node.node_id: node for node in selected_nodes}

    page_hits = (
        retrieve_hybrid_pages(
            queries,
            pages,
            {**retriever, "page_top_k": page_top_k, "top_k": page_top_k},
        )
        if use_hybrid_page
        else []
    )
    global_hits = (
        retrieve_global_region(
            queries,
            selected_nodes,
            {
                **retriever,
                "method": region_method,
                "region_top_k": global_region_top_k,
            },
        )
        if use_global_region
        else []
    )
    page_hits_by_query = group_retrieval_hits(page_hits)
    global_hits_by_query = group_retrieval_hits(global_hits)

    final_hits: list[RetrievalHit] = []
    for query in queries:
        candidates = build_evidence_candidates(
            query,
            page_hits_by_query.get(query.query_id, []),
            global_hits_by_query.get(query.query_id, []),
            nodes_by_page,
            nodes_by_id,
        )
        if use_structured_scan:
            add_structured_scan_candidates(
                query,
                nodes_by_doc.get(query.doc_id, []),
                candidates,
                top_k=structured_scan_top_k,
            )
        if use_cover_anchor:
            add_cover_anchor_candidates(
                query,
                nodes_by_doc.get(query.doc_id, []),
                candidates,
                top_k=cover_anchor_top_k,
            )
        if not candidates:
            continue

        candidate_nodes = [candidate.node for candidate in candidates.values()]
        semantic_hits = retrieve_nodes(
            [query],
            candidate_nodes,
            method=region_method,
            top_k=len(candidate_nodes),
            encoder=encoder,
            require_dense_model=require_dense_model(retriever),
            dense_batch_size=dense_batch_size(retriever),
            dense_max_seq_length=dense_max_seq_length(retriever),
        )
        for hit in semantic_hits:
            if not hit.node_id or hit.node_id not in candidates:
                continue
            candidate = candidates[hit.node_id]
            candidate.semantic_rank = hit.rank
            candidate.semantic_score = float(hit.score)

        target_slots = query_target_slots(query)
        for candidate in candidates.values():
            score_evidence_candidate(
                query, candidate, target_slots, use_slot_coverage=use_slot_coverage
            )

        selected = select_minimal_evidence_set(
            list(candidates.values()),
            target_slots if use_slot_coverage else set(),
            max_evidence_nodes=max_evidence_nodes,
            output_top_k=output_top_k,
            selection_mode=selection_mode,
        )
        covered_slots: set[str] = set()
        evidence_count = min(len(selected), max_evidence_nodes)
        for rank, candidate in enumerate(selected, start=1):
            slots = candidate.coverage_slots or set()
            if rank <= evidence_count:
                covered_slots.update(slots)
            final_hits.append(
                RetrievalHit(
                    query_id=query.query_id,
                    rank=rank,
                    score=float(candidate.combined_score),
                    doc_id=candidate.node.doc_id,
                    page_id=candidate.node.page_id,
                    node_id=candidate.node.node_id,
                    node_type=candidate.node.node_type,
                    text=candidate.node.text,
                    retriever="evidence_set_region",
                    metadata={
                        "candidate_sources": candidate_sources(candidate),
                        "coverage_slots": sorted(slots),
                        "coverage_score": candidate.coverage_score,
                        "semantic_score": candidate.semantic_score,
                        "semantic_rank": candidate.semantic_rank,
                        "page_rank": candidate.page_rank,
                        "global_rank": candidate.global_rank,
                        "structured_rank": candidate.structured_rank,
                        "structured_score": candidate.structured_score,
                        "cover_rank": candidate.cover_rank,
                        "localization_score": candidate.localization_score,
                        "selection_reason": selection_reason(candidate, slots, target_slots),
                        "evidence_set_rank": rank if rank <= evidence_count else None,
                        "covered_slots_after_selection": sorted(covered_slots),
                        "target_slots": sorted(target_slots),
                    },
                )
            )
    return final_hits


def group_retrieval_hits(hits: list[RetrievalHit]) -> dict[str, list[RetrievalHit]]:
    grouped: dict[str, list[RetrievalHit]] = {}
    for hit in sorted(hits, key=lambda item: (item.query_id, item.rank)):
        grouped.setdefault(hit.query_id, []).append(hit)
    return grouped


def build_evidence_candidates(
    query: QueryRecord,
    page_hits: list[RetrievalHit],
    global_hits: list[RetrievalHit],
    nodes_by_page: dict[str, list[EvidenceNode]],
    nodes_by_id: dict[str, EvidenceNode],
) -> dict[str, EvidenceCandidate]:
    candidates: dict[str, EvidenceCandidate] = {}
    for page_hit in page_hits:
        for node in nodes_by_page.get(page_hit.page_id, []):
            if node.doc_id != query.doc_id:
                continue
            candidate = candidates.setdefault(node.node_id, EvidenceCandidate(node=node))
            candidate.from_page_candidate = True
            if candidate.page_rank is None or page_hit.rank < candidate.page_rank:
                candidate.page_rank = page_hit.rank

    for global_hit in global_hits:
        if not global_hit.node_id:
            continue
        node = nodes_by_id.get(global_hit.node_id)
        if node is None or node.doc_id != query.doc_id:
            continue
        candidate = candidates.setdefault(node.node_id, EvidenceCandidate(node=node))
        candidate.from_global_region = True
        if candidate.global_rank is None or global_hit.rank < candidate.global_rank:
            candidate.global_rank = global_hit.rank
    return candidates


def add_structured_scan_candidates(
    query: QueryRecord,
    doc_nodes: list[EvidenceNode],
    candidates: dict[str, EvidenceCandidate],
    top_k: int,
) -> None:
    if query.question_type not in {"numeric", "comparison"}:
        return
    page_context = page_context_by_page(doc_nodes)
    scored = [
        (node, structured_numeric_scan_score(query, node, page_context.get(node.page_id, "")))
        for node in doc_nodes
        if node.text.strip()
    ]
    ranked = [
        (node, score)
        for node, score in sorted(scored, key=lambda item: item[1], reverse=True)
        if score > 0
    ][:top_k]
    for rank, (node, score) in enumerate(ranked, start=1):
        candidate = candidates.setdefault(node.node_id, EvidenceCandidate(node=node))
        candidate.from_structured_scan = True
        candidate.structured_score = max(candidate.structured_score, score)
        if candidate.structured_rank is None or rank < candidate.structured_rank:
            candidate.structured_rank = rank


def add_cover_anchor_candidates(
    query: QueryRecord,
    doc_nodes: list[EvidenceNode],
    candidates: dict[str, EvidenceCandidate],
    top_k: int,
) -> None:
    if not is_cover_query(query):
        return
    first_page_nodes = sorted(
        [node for node in doc_nodes if int(node.metadata.get("page_index", 999999)) == 1],
        key=lambda node: node.reading_order,
    )[:top_k]
    for rank, node in enumerate(first_page_nodes, start=1):
        candidate = candidates.setdefault(node.node_id, EvidenceCandidate(node=node))
        candidate.from_cover_anchor = True
        if candidate.cover_rank is None or rank < candidate.cover_rank:
            candidate.cover_rank = rank


def query_target_slots(query: QueryRecord) -> set[str]:
    question = query.question
    slots: set[str] = set()
    for metric, aliases in METRIC_ALIASES.items():
        if any(alias in question for alias in aliases):
            slots.add(f"metric:{metric}")
    for year in extract_years(question):
        slots.add(f"year:{year}")
    for unit in extract_units(question, query.metadata):
        slots.add(f"unit:{unit}")
    if needs_numeric_shape(query):
        slots.add("numeric_shape")
    for keyword in extract_question_keywords(question):
        slots.add(f"keyword:{keyword}")
    return slots


def score_evidence_candidate(
    query: QueryRecord,
    candidate: EvidenceCandidate,
    target_slots: set[str],
    use_slot_coverage: bool = True,
) -> None:
    text = normalize_text(candidate.node.text)
    coverage_slots: set[str] = set()
    for slot in target_slots:
        if slot.startswith("metric:"):
            metric = slot.removeprefix("metric:")
            if any(alias in text for alias in METRIC_ALIASES.get(metric, ())):
                coverage_slots.add(slot)
        elif slot.startswith("year:"):
            year = slot.removeprefix("year:")
            if year in text:
                coverage_slots.add(slot)
        elif slot.startswith("unit:"):
            unit = slot.removeprefix("unit:")
            if text_has_unit(text, unit):
                coverage_slots.add(slot)
        elif slot.startswith("keyword:"):
            keyword = slot.removeprefix("keyword:")
            if keyword in text:
                coverage_slots.add(slot)
        elif slot == "numeric_shape" and has_numeric_shape(text):
            coverage_slots.add(slot)

    coverage_ratio = len(coverage_slots) / max(len(target_slots), 1)
    semantic_rank_score = 1.0 / max(candidate.semantic_rank or 9999, 1)
    page_bonus = 0.25 / candidate.page_rank if candidate.page_rank else 0.0
    global_bonus = 0.25 / candidate.global_rank if candidate.global_rank else 0.0
    structured_bonus = 0.4 / candidate.structured_rank if candidate.structured_rank else 0.0
    structured_quality_bonus = min(candidate.structured_score * 0.2, 1.2)
    cover_bonus = 0.5 / candidate.cover_rank if candidate.cover_rank else 0.0
    type_bonus = node_type_bonus(query, candidate.node)
    localization_score = evidence_localization_score(query, candidate.node, coverage_slots)
    candidate.coverage_slots = coverage_slots
    candidate.coverage_score = coverage_ratio
    candidate.localization_score = localization_score
    coverage_bonus = coverage_ratio * 1.5 + len(coverage_slots) * 0.08 if use_slot_coverage else 0.0
    candidate.combined_score = (
        semantic_rank_score
        + page_bonus
        + global_bonus
        + structured_bonus
        + structured_quality_bonus
        + cover_bonus
        + coverage_bonus
        + localization_score
        + type_bonus
    )


def select_minimal_evidence_set(
    candidates: list[EvidenceCandidate],
    target_slots: set[str],
    max_evidence_nodes: int,
    output_top_k: int,
    selection_mode: str = "greedy",
) -> list[EvidenceCandidate]:
    remaining = sorted(candidates, key=lambda item: item.combined_score, reverse=True)
    if selection_mode == "single_node":
        return remaining[:output_top_k]
    selected: list[EvidenceCandidate] = []
    covered: set[str] = set()
    while remaining and len(selected) < max_evidence_nodes and covered != target_slots:
        best = max(
            remaining,
            key=lambda item: (
                len((item.coverage_slots or set()) - covered),
                item.coverage_score,
                item.combined_score,
            ),
        )
        new_slots = (best.coverage_slots or set()) - covered
        if selected and not new_slots:
            break
        selected.append(best)
        covered.update(best.coverage_slots or set())
        remaining.remove(best)

    if not selected and remaining:
        selected.append(remaining.pop(0))

    selected_ids = {candidate.node.node_id for candidate in selected}
    fillers = [
        candidate
        for candidate in sorted(candidates, key=lambda item: item.combined_score, reverse=True)
        if candidate.node.node_id not in selected_ids
    ]
    return (selected + fillers)[:output_top_k]


def structured_numeric_scan_score(
    query: QueryRecord, node: EvidenceNode, page_context: str = ""
) -> float:
    text = normalize_text(node.text)
    context = normalize_text(page_context)
    if not text:
        return 0.0
    matched_metric = matched_metric_aliases(query, text)
    if not matched_metric:
        return 0.0
    score = 1.0
    if any(year in text or year in context for year in extract_years(query.question)):
        score += 0.8
    units = extract_units(query.question, query.metadata)
    if any(text_has_unit(text, unit) or text_has_unit(context, unit) for unit in units):
        score += 0.8
    if has_numeric_shape(text):
        score += 0.9
    number_count = len(number_like_tokens(text))
    if number_count >= 3:
        score += 0.5
    elif number_count >= 1:
        score += 0.25
    if node.node_type == "table_row":
        score += 0.7
    elif node.node_type == "table_block":
        score += 0.4
    if has_structured_table_context(text) or has_structured_table_context(context):
        score += 0.7
    if has_question_section_prior(query, text) or has_question_section_prior(query, context):
        score += 0.5
    if looks_like_audit_or_narrative(text):
        score -= 0.8
    return score


def page_context_by_page(nodes: list[EvidenceNode]) -> dict[str, str]:
    grouped = group_nodes_by_page(nodes)
    return {
        page_id: " ".join(
            node.text for node in sorted(page_nodes, key=lambda item: item.reading_order)
        )
        for page_id, page_nodes in grouped.items()
    }


def evidence_localization_score(
    query: QueryRecord,
    node: EvidenceNode,
    coverage_slots: set[str],
) -> float:
    text = normalize_text(node.text)
    score = 0.0
    if query.question_type in {"numeric", "comparison"}:
        if (
            any(slot.startswith("metric:") for slot in coverage_slots)
            and "numeric_shape" in coverage_slots
        ):
            score += 0.45
        if any(slot.startswith("year:") for slot in coverage_slots) and any(
            slot.startswith("unit:") for slot in coverage_slots
        ):
            score += 0.3
        if has_structured_table_context(text):
            score += 0.35
        if node.node_type == "table_row":
            score += 0.35
        elif node.node_type == "table_block":
            score += 0.2
        if has_question_section_prior(query, text):
            score += 0.25
        if looks_like_audit_or_narrative(text):
            score -= 0.35
    elif is_cover_query(query):
        page_index = safe_page_index(node)
        if page_index == 1:
            score += 0.8
        if any(term in text for term in ("年度报告", "证券代码", "证券简称")):
            score += 0.3
    return score


def matched_metric_aliases(query: QueryRecord, normalized_text: str) -> list[str]:
    question = normalize_text(query.question)
    aliases: list[str] = []
    for _metric, metric_aliases in METRIC_ALIASES.items():
        if any(alias in question for alias in metric_aliases):
            aliases.extend(alias for alias in metric_aliases if alias in normalized_text)
    return aliases


def has_structured_table_context(text: str) -> bool:
    table_terms = ("项目", "2024", "2025", "2023", "本年比上年", "同比", "单位")
    return sum(1 for term in table_terms if term in text) >= 3


def has_question_section_prior(query: QueryRecord, text: str) -> bool:
    question = normalize_text(query.question)
    if any(term in question for term in ("营业收入", "归属于上市公司股东的净利润", "资产总额")):
        return any(term in text for term in ("主要会计数据", "财务指标", "本年比上年增减"))
    if any(term in question for term in ("现金流量净额", "经营活动")):
        return any(term in text for term in ("现金流量数据", "现金流量表", "经营活动"))
    if any(term in question for term in ("研发投入", "研发费用")):
        return any(term in text for term in ("研发投入", "研发费用", "研发人员", "研发支出"))
    if any(term in question for term in ("同比", "增减幅度", "相比上年")):
        return any(term in text for term in ("本年比上年增减", "同比", "增减"))
    return False


def looks_like_audit_or_narrative(text: str) -> bool:
    negative_terms = ("关键审计事项", "审计", "管理层", "风险", "会计政策", "确认时点")
    return sum(1 for term in negative_terms if term in text) >= 2


def is_cover_query(query: QueryRecord) -> bool:
    question = normalize_text(query.question)
    return any(term in question for term in ("报告年度", "报告标题", "首页", "标题处"))


def safe_page_index(node: EvidenceNode) -> int:
    try:
        return int(node.metadata.get("page_index", 999999))
    except (TypeError, ValueError):
        return 999999


def extract_years(text: str) -> set[str]:
    return set(re.findall(r"20\d{2}", text))


def extract_units(question: str, metadata: dict[str, Any]) -> set[str]:
    units: set[str] = set()
    answer_unit = metadata.get("answer_unit")
    if isinstance(answer_unit, str) and answer_unit.strip():
        units.add(answer_unit.strip())
    for unit in UNIT_TERMS:
        if unit in question and not any(unit in selected for selected in units):
            units.add(unit)
    return units


def needs_numeric_shape(query: QueryRecord) -> bool:
    question = query.question
    numeric_clues = ("多少", "增减", "幅度", "收入", "利润", "现金流", "资产", "负债", "研发")
    return query.question_type in {"numeric", "comparison"} or any(
        clue in question for clue in numeric_clues
    )


def has_numeric_shape(text: str) -> bool:
    number_patterns = [
        r"[(（]\s*[-+]?\d[\d,]*(?:\.\d+)?\s*[)）]",
        r"[-+]?\d[\d,]*(?:\.\d+)?\s*%",
        r"[-+]?\d[\d,]*(?:\.\d+)?\s*(?:元|万元|亿元|百分点)",
        r"\d{1,3}(?:,\d{3})+(?:\.\d+)?",
        r"[-+]?\d+\.\d+",
    ]
    return any(re.search(pattern, text) for pattern in number_patterns)


def number_like_tokens(text: str) -> list[str]:
    return re.findall(r"[-+]?[(（]?\d[\d,]*(?:\.\d+)?[)）]?%?", text)


def text_has_unit(text: str, unit: str) -> bool:
    if unit == "元":
        return bool(re.search(r"(?<![万亿])元", text))
    if unit == "%":
        return "%" in text
    return unit in text


def extract_question_keywords(question: str) -> set[str]:
    keywords: set[str] = set()
    for metric, aliases in METRIC_ALIASES.items():
        if any(alias in question for alias in aliases):
            keywords.add(metric)
    cleaned = re.sub(r"20\d{2}\s*年?度?", " ", question)
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z%]{2,}", cleaned):
        token = token.strip()
        if token in QUESTION_STOP_TERMS:
            continue
        if any(stop in token for stop in ("哪一年", "是多少", "是什么")):
            continue
        if len(token) > 12:
            continue
        keywords.add(token)
    return set(sorted(keywords)[:6])


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def node_type_bonus(query: QueryRecord, node: EvidenceNode) -> float:
    if query.question_type in {"numeric", "comparison"} and node.node_type == "table_row":
        return 0.2
    if query.question_type in {"risk_text", "text"} and node.node_type == "paragraph":
        return 0.15
    return 0.0


def candidate_sources(candidate: EvidenceCandidate) -> list[str]:
    sources = []
    if candidate.from_page_candidate:
        sources.append("hybrid_page")
    if candidate.from_global_region:
        sources.append("global_region")
    if candidate.from_structured_scan:
        sources.append("structured_numeric_scan")
    if candidate.from_cover_anchor:
        sources.append("cover_anchor")
    return sources


def selection_reason(candidate: EvidenceCandidate, slots: set[str], target_slots: set[str]) -> str:
    slot_text = ",".join(sorted(slots)) if slots else "no_slot"
    source_text = "+".join(candidate_sources(candidate)) or "candidate"
    return f"{source_text}; coverage={len(slots)}/{len(target_slots)}; slots={slot_text}"


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
    except Exception as exc:
        log_retrieval(f"Dense encoder is unavailable ({type(exc).__name__}: {exc}).")
        if "out of memory" in str(exc).lower():
            raise RuntimeError(
                "Dense retrieval exhausted accelerator memory. Reduce `dense_batch_size` and "
                "`dense_max_seq_length`, or run the experiment on a CUDA desktop."
            ) from exc
        return None


def get_sentence_transformer(model_name: str, max_seq_length: int | None = None) -> Any:
    device = os.getenv("MDR_DENSE_DEVICE") or None
    cache_key = f"{model_name}::max_seq_length={max_seq_length or 'default'}::device={device or 'auto'}"
    if cache_key in _SENTENCE_TRANSFORMER_CACHE:
        return _SENTENCE_TRANSFORMER_CACHE[cache_key]

    from sentence_transformers import SentenceTransformer

    device_label = device or "automatic device selection"
    log_retrieval(f"Loading sentence encoder `{model_name}` on {device_label} from local cache...")
    started_at = time.monotonic()
    previous_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    previous_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    if os.getenv("MDR_ALLOW_MODEL_DOWNLOAD", "0") != "1":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    try:
        model_kwargs = {"device": device} if device else {}
        try:
            model = SentenceTransformer(model_name, local_files_only=True, **model_kwargs)
        except Exception:
            if os.getenv("MDR_ALLOW_MODEL_DOWNLOAD", "0") != "1":
                raise
            model = SentenceTransformer(model_name, **model_kwargs)
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
    log_retrieval(f"Sentence encoder is ready in {time.monotonic() - started_at:.1f}s.")
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
