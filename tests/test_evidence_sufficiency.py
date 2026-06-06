from __future__ import annotations

from mmdocrag.evaluation.sufficiency import (
    check_query_evidence,
    decide_sufficiency_status,
    normalize_number,
    value_in_text,
    verify_evidence_sufficiency,
)
from mmdocrag.schemas import QueryRecord, RetrievalHit


def test_quadruple_check_covers_metric_year_unit_and_value():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        answer="100 元",
        question_type="numeric",
        evidence_node_ids=["n1"],
        metadata={"answer_unit": "元", "raw_answer_value": "100"},
    )

    result = check_query_evidence(query, "项目 2025 年 营业收入 100 元", ["n1"])

    assert result["metric_ok"]
    assert result["year_ok"]
    assert result["unit_ok"]
    assert result["value_ok"]
    assert result["missing_items"] == []


def test_quadruple_check_reports_missing_unit_and_value():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        answer="100 元",
        question_type="numeric",
        evidence_node_ids=["n1"],
        metadata={"answer_unit": "元", "raw_answer_value": "100"},
    )

    result = check_query_evidence(query, "项目 2025 年 营业收入", ["n1"])

    assert result["metric_ok"]
    assert result["year_ok"]
    assert not result["unit_ok"]
    assert not result["value_ok"]
    assert set(result["missing_items"]) == {"unit", "value"}


def test_fact_question_does_not_require_financial_metric_slot():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="这份年度报告对应的报告年度是哪一年？",
        answer="2025",
        question_type="fact",
        evidence_node_ids=["n1"],
        metadata={"source_section": "cover"},
    )

    result = check_query_evidence(query, "2025 年年度报告", ["n1"])

    assert result["covered_items"] == ["value"]
    assert result["missing_items"] == []


def test_sufficiency_status_detects_citation_mismatch():
    query = QueryRecord(
        query_id="q1",
        dataset="demo",
        doc_id="doc1",
        question="2025年营业收入是多少？",
        answer="100 元",
        question_type="numeric",
        evidence_node_ids=["gold_n1"],
        metadata={"answer_unit": "元", "raw_answer_value": "100"},
    )
    hits = [
        RetrievalHit(
            query_id="q1",
            rank=1,
            score=1.0,
            doc_id="doc1",
            page_id="p1",
            node_id="wrong_n1",
            node_type="table_row",
            text="项目 2025 年 营业收入 100 元",
            retriever="unit",
        )
    ]

    result = verify_evidence_sufficiency([query], hits, top_k=1)[0]

    assert result.status == "citation_mismatch"
    assert result.coverage_ratio == 1.0
    assert not result.citation_ok


def test_decide_sufficiency_status_for_partial_and_insufficient():
    assert (
        decide_sufficiency_status({"missing_items": ["unit"], "coverage_ratio": 0.75}, False)
        == "partial"
    )
    assert (
        decide_sufficiency_status(
            {"missing_items": ["metric", "unit"], "coverage_ratio": 0.25}, False
        )
        == "insufficient"
    )


def test_value_matching_handles_commas_parentheses_and_percent():
    assert normalize_number("(98,812.49)") == "-98812.49"
    assert value_in_text("(98,812.49)", "经营活动产生的现金流量净额(98,812.49)万元")
    assert value_in_text("-31.98%", "营业收入233,432,768,960.43同比-31.98%")


def test_value_matching_handles_values_inside_dense_table_text():
    text = "42、营业收入和营业成本 营业收入 233,432,768,960.43 343,176,440,712.96"

    assert value_in_text("233,432,768,960.43", text)
