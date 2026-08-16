from __future__ import annotations

import pytest

from mmdocrag.evaluation.metrics import (
    mrr,
    ndcg_at_k,
    page_recall_at_k,
    region_hit_at_k,
    region_mrr,
    region_ndcg_at_k,
)
from mmdocrag.retrieval.pipeline import (
    EvidenceCandidate,
    retrieve_evidence_set_region,
    retrieve_global_region,
    retrieve_hybrid_page_region,
    retrieve_hybrid_pages,
    retrieve_oracle_page_region,
    retrieve_pages,
    score_evidence_candidate,
    score_texts_with_backend,
    select_minimal_evidence_set,
    structured_numeric_scan_score,
    text_has_unit,
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


def test_dense_fallback_backend_is_explicit(monkeypatch):
    monkeypatch.setenv("MDR_DISABLE_SENTENCE_TRANSFORMERS", "1")

    result = score_texts_with_backend(
        ["营业收入是多少"], ["营业收入 100 元", "普通说明"], "dense", "BAAI/bge-m3"
    )

    assert result.backend == "dense:tfidf_fallback"
    assert result.scores[0][0] > result.scores[0][1]


def test_dense_require_model_raises_when_model_missing(monkeypatch):
    monkeypatch.setenv("MDR_DISABLE_SENTENCE_TRANSFORMERS", "1")

    with pytest.raises(RuntimeError, match="requires local SentenceTransformer model"):
        score_texts_with_backend(
            ["营业收入是多少"],
            ["营业收入 100 元"],
            "dense",
            "BAAI/bge-m3",
            require_model=True,
        )


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
    assert region_mrr(queries, hits) == 1.0
    assert region_ndcg_at_k(queries, hits, 1) == 1.0


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


def test_hybrid_page_retrieves_with_rrf_fusion():
    pages = [
        PageRecord(doc_id="doc1", page_id="doc1_p1", page_index=1, page_text="普通说明"),
        PageRecord(doc_id="doc1", page_id="doc1_p2", page_index=2, page_text="营业收入 100 元"),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="营业收入是多少？",
            evidence_page_ids=["doc1_p2"],
        )
    ]

    hits = retrieve_hybrid_pages(
        queries,
        pages,
        {
            "search_scope": "document",
            "page_methods": ["bm25", "tfidf"],
            "top_k": [1],
            "candidate_top_k": 2,
        },
    )

    assert hits[0].page_id == "doc1_p2"
    assert hits[0].retriever == "hybrid_page"


def test_hybrid_page_region_returns_region_nodes():
    pages = [
        PageRecord(doc_id="doc1", page_id="doc1_p1", page_index=1, page_text="普通说明"),
        PageRecord(doc_id="doc1", page_id="doc1_p2", page_index=2, page_text="营业收入 100 元"),
    ]
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

    hits = retrieve_hybrid_page_region(
        queries,
        pages,
        nodes,
        {
            "search_scope": "document",
            "page_methods": ["bm25", "tfidf"],
            "candidate_top_k": 2,
            "page_top_k": 1,
            "region_method": "bm25",
            "region_top_k": 1,
        },
    )

    assert hits[0].page_id == "doc1_p2"
    assert hits[0].node_id == "doc1_p2_n1"
    assert hits[0].retriever == "hybrid_page_region"


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


def test_evidence_set_region_merges_page_and_global_candidates():
    pages = [
        PageRecord(doc_id="doc1", page_id="doc1_p1", page_index=1, page_text="营业收入页面"),
        PageRecord(doc_id="doc1", page_id="doc1_p2", page_index=2, page_text="普通说明"),
    ]
    nodes = [
        EvidenceNode(
            node_id="doc1_p1_n1",
            doc_id="doc1",
            page_id="doc1_p1",
            node_type="paragraph",
            text="营业收入相关说明",
        ),
        EvidenceNode(
            node_id="doc1_p2_n1",
            doc_id="doc1",
            page_id="doc1_p2",
            node_type="table_row",
            text="营业收入 2025 年 100 元",
        ),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="2025年营业收入是多少？",
            question_type="numeric",
            evidence_page_ids=["doc1_p2"],
            evidence_node_ids=["doc1_p2_n1"],
            metadata={"answer_unit": "元"},
        )
    ]

    hits = retrieve_evidence_set_region(
        queries,
        pages,
        nodes,
        {
            "search_scope": "document",
            "page_methods": ["bm25"],
            "candidate_top_k": 1,
            "page_top_k": 1,
            "global_region_top_k": 2,
            "region_method": "bm25",
            "output_top_k": 2,
            "max_evidence_nodes": 2,
            "node_types": ["paragraph", "table_row"],
        },
    )

    assert {hit.node_id for hit in hits} == {"doc1_p1_n1", "doc1_p2_n1"}
    assert hits[0].node_id == "doc1_p2_n1"
    assert "global_region" in hits[0].metadata["candidate_sources"]
    assert all(hit.retriever == "evidence_set_region" for hit in hits)


def test_evidence_set_region_stays_inside_query_document():
    pages = [
        PageRecord(doc_id="doc1", page_id="doc1_p1", page_index=1, page_text="营业收入"),
        PageRecord(doc_id="doc2", page_id="doc2_p1", page_index=1, page_text="营业收入 999 元"),
    ]
    nodes = [
        EvidenceNode(
            node_id="doc1_p1_n1",
            doc_id="doc1",
            page_id="doc1_p1",
            node_type="table_row",
            text="营业收入 100 元",
        ),
        EvidenceNode(
            node_id="doc2_p1_n1",
            doc_id="doc2",
            page_id="doc2_p1",
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
            question_type="numeric",
            metadata={"answer_unit": "元"},
        )
    ]

    hits = retrieve_evidence_set_region(
        queries,
        pages,
        nodes,
        {
            "search_scope": "document",
            "page_methods": ["bm25"],
            "page_top_k": 1,
            "global_region_top_k": 2,
            "region_method": "bm25",
            "output_top_k": 2,
            "node_types": ["table_row"],
        },
    )

    assert hits
    assert {hit.doc_id for hit in hits} == {"doc1"}
    assert "doc2_p1_n1" not in {hit.node_id for hit in hits}


def test_evidence_set_prefers_table_row_with_required_coverage():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        question_type="numeric",
        metadata={"answer_unit": "元"},
    )
    target_slots = {
        "metric:营业收入",
        "year:2025",
        "unit:元",
        "numeric_shape",
    }
    weak = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n1",
            doc_id="doc1",
            page_id="p1",
            node_type="paragraph",
            text="营业收入相关说明",
        ),
        semantic_rank=1,
    )
    strong = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n2",
            doc_id="doc1",
            page_id="p1",
            node_type="table_row",
            text="营业收入 2025 年 100 元",
        ),
        semantic_rank=2,
    )

    score_evidence_candidate(query, weak, target_slots)
    score_evidence_candidate(query, strong, target_slots)
    selected = select_minimal_evidence_set([weak, strong], target_slots, 1, 2)

    assert selected[0].node.node_id == "n2"
    assert strong.coverage_slots == target_slots
    assert strong.combined_score > weak.combined_score


def test_evidence_set_selects_two_nodes_when_unit_and_value_are_split():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        question_type="numeric",
        metadata={"answer_unit": "元"},
    )
    target_slots = {
        "metric:营业收入",
        "year:2025",
        "unit:元",
        "numeric_shape",
    }
    unit_node = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n1",
            doc_id="doc1",
            page_id="p1",
            node_type="paragraph",
            text="单位：元 项目 2025 年",
        ),
        semantic_rank=1,
    )
    value_node = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n2",
            doc_id="doc1",
            page_id="p1",
            node_type="table_row",
            text="营业收入 100",
        ),
        semantic_rank=2,
    )

    score_evidence_candidate(query, unit_node, target_slots)
    score_evidence_candidate(query, value_node, target_slots)
    selected = select_minimal_evidence_set([unit_node, value_node], target_slots, 2, 2)

    assert {candidate.node.node_id for candidate in selected[:2]} == {"n1", "n2"}


def test_evidence_set_single_node_mode_disables_greedy_selection():
    candidates = [
        EvidenceCandidate(
            node=EvidenceNode(
                node_id="high", doc_id="doc1", page_id="p1", text="高分节点"
            ),
            combined_score=2.0,
        ),
        EvidenceCandidate(
            node=EvidenceNode(
                node_id="low", doc_id="doc1", page_id="p1", text="低分节点"
            ),
            combined_score=1.0,
        ),
    ]

    selected = select_minimal_evidence_set(
        candidates, {"metric:营业收入"}, 2, 2, selection_mode="single_node"
    )

    assert [item.node.node_id for item in selected] == ["high", "low"]


def test_evidence_set_rejects_unknown_selection_mode():
    with pytest.raises(ValueError, match="selection_mode"):
        retrieve_evidence_set_region([], [], [], {"selection_mode": "unknown"})


def test_evidence_set_does_not_rank_by_gold_answer_value():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        answer="999 元",
        question_type="numeric",
        metadata={"answer_unit": "元", "raw_answer_value": "999"},
    )
    target_slots = {"metric:营业收入", "year:2025", "unit:元", "numeric_shape"}
    covered = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n1",
            doc_id="doc1",
            page_id="p1",
            node_type="table_row",
            text="营业收入 2025 年 100 元",
        ),
        semantic_rank=1,
    )
    leaked_value_only = EvidenceCandidate(
        node=EvidenceNode(
            node_id="n2",
            doc_id="doc1",
            page_id="p1",
            node_type="paragraph",
            text="999",
        ),
        semantic_rank=2,
    )

    score_evidence_candidate(query, covered, target_slots)
    score_evidence_candidate(query, leaked_value_only, target_slots)

    assert covered.combined_score > leaked_value_only.combined_score
    assert not leaked_value_only.coverage_slots


def test_evidence_set_unit_matching_does_not_treat_yiyuan_as_yuan():
    assert text_has_unit("单位：元 营业收入 100", "元")
    assert not text_has_unit("营业收入 100 亿元", "元")
    assert text_has_unit("营业收入 100 亿元", "亿元")


def test_structured_numeric_scan_prefers_metric_table_row_over_audit_narrative():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        question_type="numeric",
        metadata={"answer_unit": "元"},
    )
    table_row = EvidenceNode(
        node_id="n1",
        doc_id="doc1",
        page_id="p1",
        node_type="table_row",
        text="营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%",
    )
    audit_text = EvidenceNode(
        node_id="n2",
        doc_id="doc1",
        page_id="p2",
        node_type="table_row",
        text="营业收入为人民币 2,334 亿元，管理层确认收入时点存在审计风险",
    )

    assert structured_numeric_scan_score(query, table_row) > structured_numeric_scan_score(
        query, audit_text
    )


def test_structured_numeric_scan_uses_same_page_header_context():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        question_type="numeric",
        metadata={"answer_unit": "元"},
    )
    row = EvidenceNode(
        node_id="n1",
        doc_id="doc1",
        page_id="p1",
        node_type="table_row",
        text="营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%",
    )
    page_header = "单位：元 项目 2025 年 2024 年 本年比上年增减 2023 年"

    assert structured_numeric_scan_score(query, row, page_header) > structured_numeric_scan_score(
        query, row
    )


def test_evidence_set_cover_query_adds_first_page_anchor():
    pages = [
        PageRecord(doc_id="doc1", page_id="doc1_p2", page_index=2, page_text="年度报告目录"),
        PageRecord(doc_id="doc1", page_id="doc1_p9", page_index=9, page_text="年度报告正文"),
    ]
    nodes = [
        EvidenceNode(
            node_id="doc1_p1_n1",
            doc_id="doc1",
            page_id="doc1_p1",
            node_type="paragraph",
            text="公司 2025 年年度报告",
            metadata={"page_index": 1},
        ),
        EvidenceNode(
            node_id="doc1_p9_n1",
            doc_id="doc1",
            page_id="doc1_p9",
            node_type="paragraph",
            text="2025 年年度报告正文",
            metadata={"page_index": 9},
        ),
    ]
    queries = [
        QueryRecord(
            query_id="q1",
            dataset="demo",
            doc_id="doc1",
            question="这份年度报告对应的报告年度是哪一年？",
            question_type="fact",
            evidence_page_ids=["doc1_p1"],
            evidence_node_ids=["doc1_p1_n1"],
        )
    ]

    hits = retrieve_evidence_set_region(
        queries,
        pages,
        nodes,
        {
            "search_scope": "document",
            "page_methods": ["bm25"],
            "page_top_k": 1,
            "global_region_top_k": 1,
            "cover_anchor_top_k": 1,
            "region_method": "bm25",
            "output_top_k": 2,
            "node_types": ["paragraph"],
        },
    )

    assert hits[0].node_id == "doc1_p1_n1"
    assert "cover_anchor" in hits[0].metadata["candidate_sources"]


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
