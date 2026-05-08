from __future__ import annotations

from mmdocrag.evaluation.metrics import mrr, page_recall_at_k, region_hit_at_k
from mmdocrag.retrieval.scoring import SimpleBM25, SimpleTfidf, reciprocal_rank_fusion
from mmdocrag.schemas import QueryRecord, RetrievalHit


def test_bm25_ranks_matching_document_first():
    scorer = SimpleBM25(["营业收入为12.8亿元", "合同服务期限为一年"])
    scores = scorer.score("营业收入是多少")

    assert scores[0] > scores[1]


def test_tfidf_ranks_matching_document_first():
    scorer = SimpleTfidf(["现金流量净额为3.4亿元", "付款方式为按季度支付"])
    scores = scorer.score("现金流量净额")

    assert scores[0] > scores[1]


def test_rrf_combines_rankings():
    scores = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])

    assert scores["b"] > scores["c"]
    assert scores["b"] > 0


def test_metrics_page_and_region_hit():
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["p1"],
            evidence_node_ids=["n1"],
        )
    ]
    hits = [
        RetrievalHit(
            query_id="q1",
            rank=1,
            score=1.0,
            doc_id="doc1",
            page_id="p1",
            node_id="n1",
            retriever="unit",
        )
    ]

    assert page_recall_at_k(queries, hits, 1) == 1.0
    assert region_hit_at_k(queries, hits, 1) == 1.0
    assert mrr(queries, hits) == 1.0
