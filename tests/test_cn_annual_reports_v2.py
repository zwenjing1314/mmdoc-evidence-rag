from __future__ import annotations

import csv

from mmdocrag.datasets.adapters import (
    _build_cn_doc_annotation_rows,
    _build_cn_page_nodes,
    _load_cn_queries,
)


def test_cn_page_nodes_split_metric_rows(tmp_path):
    text = """
    主要会计数据和财务指标
    单位：元
    项目 2025 年 2024 年 本年比上年增减
    营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%
    归属于上市公司股东的净利润 (88,556,470,495.64) (49,478,429,211.96) -78.98%
    """
    nodes = _build_cn_page_nodes(
        doc_id="万科A：2025年年度报告",
        page_id="万科A：2025年年度报告_p10",
        page_index=10,
        source_pdf=tmp_path / "report.pdf",
        text=text,
        blocks=[{"text": text, "bbox": [0.0, 0.0, 100.0, 80.0]}],
        reading_order_base=1000,
    )

    assert len(nodes) > 1
    assert any(node.node_type == "table_row" and "营业收入" in node.text for node in nodes)
    assert any("元" in node.metadata["unit_candidates"] for node in nodes)
    assert nodes[0].node_id.endswith("_n001")


def test_cn_annotation_rows_include_unit_and_evidence_text():
    page_texts = [
        "万科企业股份有限公司 2025 年度报告",
        (
            "主要会计数据和财务指标 单位：元 项目 2025 年 2024 年 本年比上年增减 "
            "营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%"
        ),
        "可能面对的风险 公司面临市场波动风险，需要持续关注销售和现金流变化。",
    ]

    rows, skipped = _build_cn_doc_annotation_rows(
        doc_id="万科A：2025年年度报告",
        company="万科A",
        page_texts=page_texts,
        questions_per_doc=8,
    )

    revenue = next(
        row for row in rows if row["question_type"] == "numeric" and "营业收入" in row["question"]
    )
    assert revenue["answer"] == "233,432,768,960.43 元"
    assert revenue["answer_unit"] == "元"
    assert "单位：元" in revenue["unit_evidence_text"]
    assert "营业收入" in revenue["value_evidence_text"]
    assert skipped


def test_cn_v2_queries_read_metadata_and_match_nodes(tmp_path):
    raw_dir = tmp_path / "cn_annual_reports"
    raw_dir.mkdir()
    csv_path = raw_dir / "qa_annotations_v2.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id",
                "doc_id",
                "question",
                "answer",
                "evidence_pages",
                "evidence_text",
                "evidence_type",
                "is_answerable",
                "notes",
                "answer_unit",
                "raw_answer_value",
                "normalized_answer",
                "value_evidence_text",
                "unit_evidence_text",
                "value_evidence_pages",
                "unit_evidence_pages",
                "question_type",
                "difficulty",
                "source_section",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "query_id": "cn_v2_q0001",
                "doc_id": "doc",
                "question": "营业收入是多少？",
                "answer": "100 元",
                "evidence_pages": "doc_p1",
                "evidence_text": "单位：元 营业收入 100",
                "evidence_type": "numeric",
                "is_answerable": "true",
                "answer_unit": "元",
                "raw_answer_value": "100",
                "normalized_answer": "100 元",
                "value_evidence_text": "营业收入 100",
                "unit_evidence_text": "单位：元",
                "question_type": "numeric",
                "difficulty": "medium",
                "source_section": "main_accounting_data",
            }
        )
    nodes = _build_cn_page_nodes(
        doc_id="doc",
        page_id="doc_p1",
        page_index=1,
        source_pdf=tmp_path / "doc.pdf",
        text="单位：元 营业收入 100",
        blocks=[],
        reading_order_base=1,
    )

    queries = _load_cn_queries(raw_dir, "cn_annual_reports", {"doc_p1": nodes})

    assert queries[0].query_id == "cn_v2_q0001"
    assert queries[0].question_type == "numeric"
    assert queries[0].metadata["answer_unit"] == "元"
    assert queries[0].metadata["annotation_file"] == "qa_annotations_v2.csv"
    assert queries[0].metadata["node_match_status"] == "matched"
    assert queries[0].evidence_node_ids
