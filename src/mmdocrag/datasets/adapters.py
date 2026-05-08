from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from mmdocrag.io import write_processed_dataset
from mmdocrag.paths import data_root
from mmdocrag.schemas import DocumentRecord, EvidenceNode, PageRecord, QueryRecord


@dataclass(frozen=True)
class PrepareResult:
    dataset: str
    processed_dir: Path
    documents: int
    pages: int
    nodes: int
    queries: int
    message: str


def prepare_dataset(dataset: str, limit_docs: int | None = None) -> PrepareResult:
    if dataset == "demo":
        return prepare_demo(limit_docs=limit_docs)
    if dataset == "mmdocir":
        return prepare_mmdocir(limit_docs=limit_docs)
    if dataset in {"cn_annual_reports", "cn_reports"}:
        return prepare_cn_annual_reports(limit_docs=limit_docs)
    raise ValueError(f"Unknown dataset: {dataset}. Choose demo, mmdocir, or cn_annual_reports.")


def prepare_demo(limit_docs: int | None = None) -> PrepareResult:
    dataset = "demo"
    processed_dir = data_root() / "processed" / dataset
    documents = [
        DocumentRecord(
            doc_id="demo_finance_2025",
            dataset=dataset,
            title="2025 Annual Report Demo",
            source_path="demo://finance",
            domain="annual_report",
            language="zh",
            num_pages=2,
            metadata={"company": "示例科技"},
        ),
        DocumentRecord(
            doc_id="demo_contract_001",
            dataset=dataset,
            title="Contract Review Demo",
            source_path="demo://contract",
            domain="contract",
            language="zh",
            num_pages=1,
            metadata={"contract_type": "service"},
        ),
    ]
    if limit_docs is not None:
        documents = documents[:limit_docs]
    allowed = {doc.doc_id for doc in documents}
    pages = [
        PageRecord(
            doc_id="demo_finance_2025",
            page_id="demo_finance_2025_p1",
            page_index=1,
            page_text="示例科技2025年营业收入为12.8亿元，同比增长18%。研发投入为2.1亿元。",
            metadata={"section": "主要会计数据"},
        ),
        PageRecord(
            doc_id="demo_finance_2025",
            page_id="demo_finance_2025_p2",
            page_index=2,
            page_text="现金流量表显示，经营活动产生的现金流量净额为3.4亿元。",
            metadata={"section": "现金流量"},
        ),
        PageRecord(
            doc_id="demo_contract_001",
            page_id="demo_contract_001_p1",
            page_index=1,
            page_text="本合同服务期限为2025年1月1日至2025年12月31日。付款方式为按季度支付。",
            metadata={"section": "合同条款"},
        ),
    ]
    pages = [page for page in pages if page.doc_id in allowed]
    nodes = [
        EvidenceNode(
            node_id="demo_finance_2025_p1_n1",
            doc_id="demo_finance_2025",
            page_id="demo_finance_2025_p1",
            node_type="paragraph",
            text="示例科技2025年营业收入为12.8亿元，同比增长18%。",
            reading_order=1,
            source="demo",
            confidence=1.0,
        ),
        EvidenceNode(
            node_id="demo_finance_2025_p1_n2",
            doc_id="demo_finance_2025",
            page_id="demo_finance_2025_p1",
            node_type="table",
            bbox=[80, 120, 520, 360],
            text="主要财务指标：营业收入12.8亿元；研发投入2.1亿元。",
            reading_order=2,
            source="demo",
            confidence=1.0,
        ),
        EvidenceNode(
            node_id="demo_finance_2025_p2_n1",
            doc_id="demo_finance_2025",
            page_id="demo_finance_2025_p2",
            node_type="paragraph",
            text="经营活动产生的现金流量净额为3.4亿元。",
            reading_order=1,
            source="demo",
            confidence=1.0,
        ),
        EvidenceNode(
            node_id="demo_contract_001_p1_n1",
            doc_id="demo_contract_001",
            page_id="demo_contract_001_p1",
            node_type="paragraph",
            text="本合同服务期限为2025年1月1日至2025年12月31日。",
            reading_order=1,
            source="demo",
            confidence=1.0,
        ),
    ]
    nodes = [node for node in nodes if node.doc_id in allowed]
    queries = [
        QueryRecord(
            query_id="demo_q1",
            dataset=dataset,
            doc_id="demo_finance_2025",
            question="示例科技2025年营业收入是多少？",
            answer="12.8亿元",
            question_type="numeric",
            evidence_page_ids=["demo_finance_2025_p1"],
            evidence_node_ids=["demo_finance_2025_p1_n1", "demo_finance_2025_p1_n2"],
        ),
        QueryRecord(
            query_id="demo_q2",
            dataset=dataset,
            doc_id="demo_finance_2025",
            question="经营活动产生的现金流量净额是多少？",
            answer="3.4亿元",
            question_type="numeric",
            evidence_page_ids=["demo_finance_2025_p2"],
            evidence_node_ids=["demo_finance_2025_p2_n1"],
        ),
        QueryRecord(
            query_id="demo_q3",
            dataset=dataset,
            doc_id="demo_contract_001",
            question="合同服务期限是什么？",
            answer="2025年1月1日至2025年12月31日",
            question_type="fact",
            evidence_page_ids=["demo_contract_001_p1"],
            evidence_node_ids=["demo_contract_001_p1_n1"],
        ),
    ]
    queries = [query for query in queries if query.doc_id in allowed]
    write_processed_dataset(processed_dir, documents, pages, nodes, queries)
    return PrepareResult(dataset, processed_dir, len(documents), len(pages), len(nodes), len(queries), "Demo dataset prepared.")


def prepare_mmdocir(limit_docs: int | None = None) -> PrepareResult:
    dataset = "mmdocir"
    raw_dir = data_root() / "raw" / dataset
    processed_dir = data_root() / "processed" / dataset
    raw_files = _visible_files(raw_dir)
    if not raw_files:
        _write_missing_data_note(
            processed_dir,
            "MMDocIR raw data not found. Put downloaded files under data/raw/mmdocir or run `mdr prepare --dataset demo`.",
        )
        return PrepareResult(dataset, processed_dir, 0, 0, 0, 0, "MMDocIR raw data not found.")

    documents, pages, nodes, queries = _generic_prepare_from_tables(dataset, raw_files, limit_docs)
    write_processed_dataset(processed_dir, documents, pages, nodes, queries)
    return PrepareResult(dataset, processed_dir, len(documents), len(pages), len(nodes), len(queries), "MMDocIR generic preparation completed.")


def prepare_cn_annual_reports(limit_docs: int | None = None) -> PrepareResult:
    dataset = "cn_annual_reports"
    raw_dir = data_root() / "raw" / dataset
    pdf_dir = raw_dir / "pdfs"
    processed_dir = data_root() / "processed" / dataset
    pdfs = sorted(path for path in pdf_dir.glob("*.pdf") if path.is_file())
    if limit_docs is not None:
        pdfs = pdfs[:limit_docs]
    if not pdfs:
        processed_dir.mkdir(parents=True, exist_ok=True)
        template = raw_dir / "qa_annotations_template.csv"
        template.parent.mkdir(parents=True, exist_ok=True)
        if not template.exists():
            with template.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "query_id",
                        "doc_id",
                        "question",
                        "answer",
                        "evidence_pages",
                        "evidence_text",
                        "evidence_type",
                        "is_answerable",
                        "notes",
                    ]
                )
        _write_missing_data_note(
            processed_dir,
            "No Chinese annual report PDFs found. Put PDFs under data/raw/cn_annual_reports/pdfs and fill qa_annotations_template.csv.",
        )
        return PrepareResult(dataset, processed_dir, 0, 0, 0, 0, "Chinese annual report PDFs not found; annotation template generated.")

    documents: list[DocumentRecord] = []
    pages: list[PageRecord] = []
    nodes: list[EvidenceNode] = []
    for index, pdf in enumerate(pdfs, start=1):
        doc_id = pdf.stem
        page_count = _safe_pdf_page_count(pdf)
        documents.append(
            DocumentRecord(
                doc_id=doc_id,
                dataset=dataset,
                title=pdf.stem,
                source_path=str(pdf),
                domain="annual_report",
                language="zh",
                num_pages=page_count,
            )
        )
        pages.append(
            PageRecord(
                doc_id=doc_id,
                page_id=f"{doc_id}_p1",
                page_index=1,
                page_text="",
                metadata={"note": "PDF registered; text parsing will be added in the next sprint."},
            )
        )
        nodes.append(
            EvidenceNode(
                node_id=f"{doc_id}_p1_n1",
                doc_id=doc_id,
                page_id=f"{doc_id}_p1",
                node_type="document_placeholder",
                text=pdf.stem,
                reading_order=index,
                source="pdf_list",
            )
        )
    queries = _load_cn_queries(raw_dir, dataset)
    write_processed_dataset(processed_dir, documents, pages, nodes, queries)
    return PrepareResult(dataset, processed_dir, len(documents), len(pages), len(nodes), len(queries), "Chinese annual reports registered.")


def _visible_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(file for file in path.rglob("*") if file.is_file() and file.name != ".gitkeep")


def _write_missing_data_note(processed_dir: Path, message: str) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "README.md").write_text(message + "\n", encoding="utf-8")


def _generic_prepare_from_tables(
    dataset: str, raw_files: list[Path], limit_docs: int | None
) -> tuple[list[DocumentRecord], list[PageRecord], list[EvidenceNode], list[QueryRecord]]:
    records: list[dict[str, Any]] = []
    for raw_file in raw_files:
        records.extend(_read_table_like(raw_file))
    if not records:
        return [], [], [], []
    doc_ids = []
    for row in records:
        doc_id = str(row.get("doc_id") or row.get("document_id") or row.get("pdf_id") or row.get("file_name") or "doc_001")
        if doc_id not in doc_ids:
            doc_ids.append(doc_id)
    if limit_docs is not None:
        doc_ids = doc_ids[:limit_docs]
    allowed = set(doc_ids)
    documents = [
        DocumentRecord(doc_id=doc_id, dataset=dataset, title=doc_id, language="mixed") for doc_id in doc_ids
    ]
    pages_by_id: dict[str, PageRecord] = {}
    nodes: list[EvidenceNode] = []
    queries: list[QueryRecord] = []
    for idx, row in enumerate(records, start=1):
        doc_id = str(row.get("doc_id") or row.get("document_id") or row.get("pdf_id") or row.get("file_name") or "doc_001")
        if doc_id not in allowed:
            continue
        page_index = int(row.get("page_index") or row.get("page") or row.get("page_id") or 1)
        page_id = str(row.get("page_id") or f"{doc_id}_p{page_index}")
        text = str(row.get("text") or row.get("page_text") or row.get("content") or row.get("answer") or "")
        pages_by_id.setdefault(
            page_id,
            PageRecord(doc_id=doc_id, page_id=page_id, page_index=page_index, page_text=text),
        )
        nodes.append(
            EvidenceNode(
                node_id=str(row.get("node_id") or f"{page_id}_n{idx}"),
                doc_id=doc_id,
                page_id=page_id,
                node_type=str(row.get("node_type") or row.get("type") or "paragraph"),
                text=text,
                reading_order=idx,
                source=str(row.get("_source_file", "generic")),
            )
        )
        question = row.get("question") or row.get("query")
        if question:
            queries.append(
                QueryRecord(
                    query_id=str(row.get("query_id") or f"q{idx}"),
                    dataset=dataset,
                    doc_id=doc_id,
                    question=str(question),
                    answer=str(row.get("answer") or ""),
                    evidence_page_ids=[page_id],
                    evidence_node_ids=[nodes[-1].node_id],
                )
            )
    return documents, list(pages_by_id.values()), nodes, queries


def _read_table_like(path: Path) -> list[dict[str, Any]]:
    try:
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("data", [])
        elif path.suffix == ".csv":
            rows = pl.read_csv(path).to_dicts()
        elif path.suffix == ".parquet":
            rows = pl.read_parquet(path).to_dicts()
        else:
            return []
    except Exception:
        return []
    for row in rows:
        row["_source_file"] = str(path)
    return rows


def _safe_pdf_page_count(path: Path) -> int:
    try:
        import fitz

        with fitz.open(path) as doc:
            return len(doc)
    except Exception:
        return 0


def _load_cn_queries(raw_dir: Path, dataset: str) -> list[QueryRecord]:
    candidates = [raw_dir / "qa_annotations.csv", raw_dir / "qa_annotations.xlsx"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        frame = pl.read_excel(candidate) if candidate.suffix == ".xlsx" else pl.read_csv(candidate)
        queries = []
        for idx, row in enumerate(frame.to_dicts(), start=1):
            doc_id = str(row.get("doc_id") or "")
            pages = str(row.get("evidence_pages") or "")
            queries.append(
                QueryRecord(
                    query_id=str(row.get("query_id") or f"cn_q{idx}"),
                    dataset=dataset,
                    doc_id=doc_id,
                    question=str(row.get("question") or ""),
                    answer=str(row.get("answer") or ""),
                    evidence_page_ids=[item.strip() for item in pages.split(";") if item.strip()],
                    is_answerable=str(row.get("is_answerable", "true")).lower() not in {"false", "0", "no"},
                    metadata={"evidence_text": row.get("evidence_text"), "notes": row.get("notes")},
                )
            )
        return queries
    return []
