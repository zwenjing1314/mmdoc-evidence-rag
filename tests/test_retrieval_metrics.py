from __future__ import annotations

from mmdocrag.evaluation.metrics import mrr, ndcg_at_k, page_recall_at_k, region_hit_at_k
from mmdocrag.retrieval.pipeline import (
    retrieve_global_region,
    retrieve_oracle_page_region,
    retrieve_pages,
)
from mmdocrag.retrieval.scoring import SimpleBM25, SimpleTfidf, reciprocal_rank_fusion
from mmdocrag.schemas import EvidenceNode, PageRecord, QueryRecord, RetrievalHit


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


def test_document_scope_retrieves_only_query_document_pages():
    pages = [
        PageRecord(
            doc_id="doc1", page_id="doc1_p1", page_index=1, page_text="本页是目标年报的普通说明"
        ),
        PageRecord(doc_id="doc2", page_id="doc2_p1", page_index=1, page_text="营业收入 999 元"),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["doc1_p1"],
        )
    ]

    corpus_hits = retrieve_pages(queries, pages, method="bm25", top_k=1, search_scope="corpus")
    document_hits = retrieve_pages(queries, pages, method="bm25", top_k=1, search_scope="document")

    assert corpus_hits[0].doc_id == "doc2"
    assert document_hits[0].doc_id == "doc1"
    assert document_hits[0].page_id == "doc1_p1"


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


def test_global_region_retrieves_nodes_directly():
    nodes = [
        EvidenceNode(
            node_id="doc1_p1_n1",
            doc_id="doc1",
            page_id="doc1_p1",
            node_type="paragraph",
            text="普通说明",
        ),
        EvidenceNode(
            node_id="doc1_p2_n1",
            doc_id="doc1",
            page_id="doc1_p2",
            node_type="table_row",
            text="营业收入 100 元",
        ),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["doc1_p2"],
            evidence_node_ids=["doc1_p2_n1"],
        )
    ]

    hits = retrieve_global_region(
        queries, nodes, {"search_scope": "document", "method": "bm25", "region_top_k": 1}
    )

    assert hits[0].node_id == "doc1_p2_n1"
    assert hits[0].page_id == "doc1_p2"
    assert hits[0].retriever == "global_region"


def test_oracle_page_region_only_searches_gold_pages():
    nodes = [
        EvidenceNode(
            node_id="doc1_p1_n1",
            doc_id="doc1",
            page_id="doc1_p1",
            node_type="paragraph",
            text="目标证据页上的普通说明",
        ),
        EvidenceNode(
            node_id="doc1_p2_n1",
            doc_id="doc1",
            page_id="doc1_p2",
            node_type="table_row",
            text="营业收入 999 元",
        ),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["doc1_p1"],
            evidence_node_ids=["doc1_p1_n1"],
        )
    ]

    hits = retrieve_oracle_page_region(queries, nodes, {"method": "bm25", "region_top_k": 1})

    assert hits[0].node_id == "doc1_p1_n1"
    assert hits[0].page_id == "doc1_p1"
    assert hits[0].retriever == "oracle_page_region"


def test_ndcg_does_not_double_count_same_gold_page_for_node_hits():
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["p1"],
            evidence_node_ids=["n2"],
        )
    ]
    hits = [
        RetrievalHit(
            query_id="q1",
            rank=1,
            score=2.0,
            doc_id="doc1",
            page_id="p1",
            node_id="n1",
            retriever="unit",
        ),
        RetrievalHit(
            query_id="q1",
            rank=2,
            score=1.0,
            doc_id="doc1",
            page_id="p1",
            node_id="n2",
            retriever="unit",
        ),
    ]

    assert ndcg_at_k(queries, hits, 2) <= 1.0
    assert ndcg_at_k(queries, hits, 2) < 1.0
