from __future__ import annotations

import math

from mmdocrag.schemas import QueryRecord, RetrievalHit


def group_hits(hits: list[RetrievalHit]) -> dict[str, list[RetrievalHit]]:
    grouped: dict[str, list[RetrievalHit]] = {}
    for hit in sorted(hits, key=lambda item: (item.query_id, item.rank)):
        grouped.setdefault(hit.query_id, []).append(hit)
    return grouped


def page_recall_at_k(queries: list[QueryRecord], hits: list[RetrievalHit], k: int) -> float:
    grouped = group_hits(hits)
    total = 0
    correct = 0
    for query in queries:
        if not query.evidence_page_ids:
            continue
        total += 1
        predicted = {hit.page_id for hit in grouped.get(query.query_id, [])[:k]}
        if predicted.intersection(query.evidence_page_ids):
            correct += 1
    return correct / total if total else 0.0


def mrr(queries: list[QueryRecord], hits: list[RetrievalHit]) -> float:
    grouped = group_hits(hits)
    total = 0
    score = 0.0
    for query in queries:
        if not query.evidence_page_ids and not query.evidence_node_ids:
            continue
        total += 1
        target_pages = set(query.evidence_page_ids)
        target_nodes = set(query.evidence_node_ids)
        for hit in grouped.get(query.query_id, []):
            if hit.page_id in target_pages or (hit.node_id and hit.node_id in target_nodes):
                score += 1 / hit.rank
                break
    return score / total if total else 0.0


def ndcg_at_k(queries: list[QueryRecord], hits: list[RetrievalHit], k: int) -> float:
    grouped = group_hits(hits)
    total = 0
    score = 0.0
    for query in queries:
        targets = set(query.evidence_page_ids) | set(query.evidence_node_ids)
        if not targets:
            continue
        total += 1
        dcg = 0.0
        for hit in grouped.get(query.query_id, [])[:k]:
            item_ids = {hit.page_id}
            if hit.node_id:
                item_ids.add(hit.node_id)
            relevance = 1 if item_ids.intersection(targets) else 0
            dcg += relevance / math.log2(hit.rank + 1)
        ideal_hits = min(len(targets), k)
        idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        score += dcg / idcg if idcg else 0.0
    return score / total if total else 0.0


def region_hit_at_k(queries: list[QueryRecord], hits: list[RetrievalHit], k: int) -> float:
    grouped = group_hits(hits)
    total = 0
    correct = 0
    for query in queries:
        if not query.evidence_node_ids:
            continue
        total += 1
        predicted = {hit.node_id for hit in grouped.get(query.query_id, [])[:k] if hit.node_id}
        if predicted.intersection(query.evidence_node_ids):
            correct += 1
    return correct / total if total else 0.0


def evaluate_metrics(queries: list[QueryRecord], hits: list[RetrievalHit]) -> dict[str, float]:
    return {
        "page_recall@1": page_recall_at_k(queries, hits, 1),
        "page_recall@5": page_recall_at_k(queries, hits, 5),
        "page_recall@10": page_recall_at_k(queries, hits, 10),
        "mrr": mrr(queries, hits),
        "ndcg@5": ndcg_at_k(queries, hits, 5),
        "ndcg@10": ndcg_at_k(queries, hits, 10),
        "region_hit@5": region_hit_at_k(queries, hits, 5),
    }
