from __future__ import annotations

import csv
import json
import re
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


CN_ANNOTATION_FIELDS = [
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
]

FINANCIAL_KEYWORDS = {
    "营业收入",
    "归属于上市公司股东的净利润",
    "经营活动产生的现金流量净额",
    "研发投入",
    "研发费用",
    "资产总额",
    "负债合计",
}

NUMBER_PATTERN = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")
PERCENT_PATTERN = re.compile(r"-?\d+(?:\.\d+)?%")
UNIT_PATTERN = re.compile(r"单位[：:]\s*([人民币元万元亿元百万元千元]+)")


# 不同数据集选择不同的处理函数
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
    raw_dir = data_root() / "raw" / dataset  # 中文年报原始数据上一级目录路径
    pdf_dir = raw_dir / "pdfs"  # 中文年报原始数据路径
    processed_dir = data_root() / "processed" / dataset  # 处理后的中文年报数据
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

    documents: list[DocumentRecord] = []  # 文档列表
    pages: list[PageRecord] = []  # 页面列表
    nodes: list[EvidenceNode] = []  # 节点列表
    for pdf_index, pdf in enumerate(pdfs, start=1):
        doc_id = pdf.stem  # 获取 pdf 文件去除 .pdf 后的文件名作为 doc_id 字段
        # extracted_pages 返回的是
        #     items = [
        #     {第1页数据},
        #     {第2页数据}]
        extracted_pages = _extract_pdf_page_items(pdf)  # 获取所有页面的内容，
        page_count = len(extracted_pages)
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
        for page_index, page_item in enumerate(extracted_pages, start=1):
            page_id = f"{doc_id}_p{page_index}"
            page_text = str(page_item.get("text") or "")
            normalized_text = _clean_text(page_text)  # 清理和规范化从 PDF 提取的文本
            pages.append(
                PageRecord(
                    doc_id=doc_id,
                    page_id=page_id,
                    page_index=page_index,
                    page_text=normalized_text,
                    ocr_text=normalized_text,
                    # 是一个字典，用于存储额外的、可选的元数据
                    metadata={"source_pdf": str(pdf),   # 来源 PDF 文件的完整路径
                              "parser": "pymupdf"}  # 使用的解析器名称
                    ,
                )
            )
            nodes.extend(
                # _build_cn_page_nodes() 返回一个临时列表
                #   page1_nodes = [node_p1_001, node_p1_002, node_p1_003]
                # extend 将这个列表中的每个元素逐个添加
                #   等价于：
                #   nodes.append(node_p1_001)
                #   nodes.append(node_p1_002)
                #   nodes.append(node_p1_003)
                _build_cn_page_nodes(
                    doc_id=doc_id,
                    page_id=page_id,
                    page_index=page_index,
                    source_pdf=pdf,
                    text=page_text,
                    blocks=list(page_item.get("blocks") or []),
                    reading_order_base=pdf_index * 100000 + page_index * 1000,
                )
            )
    nodes_by_page: dict[str, list[EvidenceNode]] = {}
    """
    等价于
    if node.page_id not in nodes_by_page:
        nodes_by_page[node.page_id] = []
        nodes_by_page[node.page_id].append(node)
    """
    for node in nodes:
        nodes_by_page.setdefault(node.page_id, []).append(node)
    queries = _load_cn_queries(raw_dir, dataset, nodes_by_page=nodes_by_page)
    write_processed_dataset(processed_dir, documents, pages, nodes, queries)
    return PrepareResult(
        dataset,
        processed_dir,
        len(documents),
        len(pages),
        len(nodes),
        len(queries),
        "Chinese annual reports parsed with paragraph/table-row evidence nodes.",
    )


def build_cn_annotations(questions_per_doc: int = 8, limit_docs: int | None = None) -> Path:
    dataset = "cn_annual_reports"
    raw_dir = data_root() / "raw" / dataset
    pdf_dir = raw_dir / "pdfs"
    pdfs = sorted(path for path in pdf_dir.glob("*.pdf") if path.is_file())
    if limit_docs is not None:
        pdfs = pdfs[:limit_docs]
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found under {pdf_dir}")

    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    query_index = 1
    for pdf in pdfs:
        doc_id = pdf.stem
        company = _company_name_from_doc_id(doc_id)
        page_items = _extract_pdf_page_items(pdf)
        page_texts = [_clean_text(str(item.get("text") or "")) for item in page_items]
        doc_rows, doc_skipped = _build_cn_doc_annotation_rows(
            doc_id=doc_id,
            company=company,
            page_texts=page_texts,
            questions_per_doc=questions_per_doc,
        )
        skipped.extend([f"{doc_id}: {item}" for item in doc_skipped])
        for row in doc_rows:
            row["query_id"] = f"cn_v2_q{query_index:04d}"
            query_index += 1
            rows.append(row)

    output = raw_dir / "qa_annotations_v2.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CN_ANNOTATION_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CN_ANNOTATION_FIELDS})

    log = raw_dir / "qa_annotations_v2_generation_log.md"
    log.write_text(
        "# QA Annotations V2 Generation Log\n\n"
        f"- PDFs: {len(pdfs)}\n"
        f"- Questions: {len(rows)}\n"
        f"- Questions per doc target: {questions_per_doc}\n\n"
        "## Skipped Items\n\n"
        + ("\n".join(f"- {item}" for item in skipped) if skipped else "- None\n"),
        encoding="utf-8",
    )
    return output


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


def _extract_pdf_page_items(path: Path) -> list[dict[str, Any]]:
    try:
        import fitz

        items: list[dict[str, Any]] = []
        with fitz.open(path) as doc:  # 打开 PDF 文档
            for page in doc:  # 第1层循环：遍历每一页
                blocks = []  # 当前页面的文本块列表
                for block in page.get_text("blocks") or []:  # ← 第2层循环：遍历每个文本块  block 一般返回7个字段 x1, y1, x2, y2, text, block_no, block_type
                    if len(block) < 5:  # 字段小于等于 5，则忽略
                        continue
                    text = _clean_text(str(block[4]))
                    if not text:
                        continue
                    blocks.append(
                        {
                            "bbox": [float(block[0]), float(block[1]), float(block[2]), float(block[3])],
                            "text": text,
                        }
                    )
                items.append({"text": page.get_text("text") or "", "blocks": blocks})
        return items
    except Exception:
        return [{"text": text, "blocks": []} for text in _extract_pdf_pages(path)]


def _extract_pdf_pages(path: Path) -> list[str]:
    try:
        import fitz

        with fitz.open(path) as doc:
            return [page.get_text("text") or "" for page in doc]
    except Exception:
        return []


# 这是一个文本标准化函数，用于清理和规范化从 PDF 提取的文本
def _clean_text(text: str) -> str:
    # (text or "") - 空值保护
    # .replace("\u3000", " ") - 用半角空格（ASCII 32）替换全角空格
    # 这里调用的是无参数的 split()
    return " ".join((text or "").replace("\u3000", " ").split())


def _build_cn_page_nodes(
    doc_id: str,
    page_id: str,
    page_index: int,
    source_pdf: Path,
    text: str,
    blocks: list[dict[str, Any]],
    reading_order_base: int,
) -> list[EvidenceNode]:
    raw_chunks = _block_chunks(blocks) or _fallback_text_chunks(text)  # 将 PyMuPDF 提取的 blocks 列表转换为简化的 chunk 字典列表。 当无法获取 PDF blocks 时，基于文本规则将纯文本切分成 chunks
    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in raw_chunks:
        # 清理文本
        chunk_text = _clean_text(str(chunk.get("text") or ""))
        if not chunk_text:
            continue  # 跳过空文本
        # 提取财务指标行（细粒度）
        for metric_chunk in _metric_row_chunks(chunk_text):
            # 生成唯一标识（标准化 + 截断）
            key = _normalize_for_match(metric_chunk["text"])[:180]
            # key = "营业收入233,432,768,960.43343,176,440,712.96-31.98%"
            # 检查key是否已存在
            if key and key not in seen:
                seen.add(key)
                # **metric_chunk 展开 {"text": ..., "node_type": "table_row"}
                chunks.append({**metric_chunk, "bbox": chunk.get("bbox")})
        # 处理普通文本块（粗粒度）
        key = _normalize_for_match(chunk_text)[:220]  # 比财务指标的 180 字符更长. 因为普通段落的多样性更高，需要更长的指纹来确保唯一性
        if len(chunk_text) >= 12 and key not in seen:
            seen.add(key)
            chunks.append(
                {
                    "text": chunk_text[:900],  # 限制长度
                    "node_type": "table_block" if _looks_like_table_block(chunk_text) else "paragraph",
                    "bbox": chunk.get("bbox"),
                }
            )

    # 前面的切分逻辑没有产生任何 chunks（例如页面完全是空白的），则创建一个默认的节点，避免页面没有任何证据节点
    if not chunks:
        chunks.append({"text": _clean_text(text) or page_id, "node_type": "paragraph", "bbox": None})

    # 是将切分好的文本片段（chunks）转换为标准的证据节点（EvidenceNode）对象，这是页面处理的最后一步
    unit_candidates = _unit_candidates(_clean_text(text))
    nodes: list[EvidenceNode] = []
    for index, chunk in enumerate(chunks, start=1):
        nodes.append(
            EvidenceNode(
                node_id=f"{page_id}_n{index:03d}",
                doc_id=doc_id,
                page_id=page_id,
                node_type=str(chunk.get("node_type") or "paragraph"),
                bbox=chunk.get("bbox"),
                text=str(chunk.get("text") or ""),
                reading_order=reading_order_base + index,
                source="pymupdf_blocks",
                confidence=1.0,
                metadata={
                    "chunk_method": "pymupdf_block_metric_rows" if blocks else "text_fallback",
                    "page_index": page_index,
                    "unit_candidates": unit_candidates,
                    "source_pdf": str(source_pdf),
                },
            )
        )
    return nodes

# 将 PyMuPDF 提取的 blocks 列表转换为简化的 chunk 字典列表
def _block_chunks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"text": block.get("text", ""), "bbox": block.get("bbox")}
        for block in blocks
        if _clean_text(str(block.get("text") or ""))
    ]


# 当无法获取 PDF blocks 时，基于文本规则将纯文本切分成 chunks
def _fallback_text_chunks(text: str) -> list[dict[str, Any]]:
    # 步骤1：按行分割并清理
    lines = [_clean_text(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line]  # 去除空行
    chunks: list[dict[str, Any]] = []
    current: list[str] = []  # 累积普通文本行
    for line in lines:
        # 步骤2：检测是否是财务数据行
        is_financial_line = _contains_financial_keyword(line) and bool(NUMBER_PATTERN.search(line))  # 子串关键字检查和数字检测，同时满足两个条件才认为是财务数据行
        if is_financial_line:
            # 步骤3a：如果是财务行，先保存之前累积的普通文本
            if current:
                chunks.append({"text": " ".join(current), "bbox": None})
                current = []
            # 步骤3b：财务行单独成为一个 chunk
            chunks.append({"text": line, "bbox": None})
            continue
        # 步骤4：普通行累积到 current
        current.append(line)
        # 步骤5：如果累积文本超过 260 字符，切分为一个 chunk
        if len(" ".join(current)) >= 260:
            chunks.append({"text": " ".join(current), "bbox": None})
            current = []
    # 步骤6：处理剩余的文本
    if current:
        chunks.append({"text": " ".join(current), "bbox": None})
    return chunks

# 从文本中提取财务指标数据行
"""
这个函数会从 chunk_text 中提取所有包含财务关键词的数据行
示例输入：
chunk_text = '''
主要会计数据
营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%
净利润 88,556,470,495.64 49,478,429,211.96 -78.98%
'''

输出：
metric_chunks = [
    {
        "text": "营业收入 233,432,768,960.43 343,176,440,712.96 -31.98%",
        "node_type": "table_row"
    },
    {
        "text": "净利润 88,556,470,495.64 49,478,429,211.96 -78.98%",
        "node_type": "table_row"
    }
]
"""
def _metric_row_chunks(text: str) -> list[dict[str, str]]:
    chunks = []
    for keyword in FINANCIAL_KEYWORDS:
        position = text.find(keyword)
        if position < 0:
            continue
        window = text[position : position + 360]
        if not NUMBER_PATTERN.search(window):
            continue
        chunks.append({"text": window, "node_type": "table_row"})  # 创建财务数据行 chunk
    return chunks


# 进行表格块判断检查
def _looks_like_table_block(text: str) -> bool:
    numbers = NUMBER_PATTERN.findall(text)
    # 包含 ≥3 个数字 → 可能是表格。 包含财务关键词 → 可能是财务表格
    return len(numbers) >= 3 or _contains_financial_keyword(text)


def _contains_financial_keyword(text: str) -> bool:
    return any(keyword in text for keyword in FINANCIAL_KEYWORDS)  # 字符串 in 字符串 → 子串检查


# 从整页文本中提取可能的数值单位（如"元"、"万元"、"亿元"等），用于后续理解财务数据的量级
def _unit_candidates(text: str) -> list[str]:
    units = []
    for match in UNIT_PATTERN.finditer(text):
        unit = match.group(1)
        if unit not in units:
            units.append(unit)
    return units[:5]  # 最多返回5个单位


def _build_cn_doc_annotation_rows(
    doc_id: str,
    company: str,
    page_texts: list[str],
    questions_per_doc: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    first_page = page_texts[0] if page_texts else ""
    year = _infer_report_year(doc_id, first_page)
    title = _infer_report_title(first_page, year)

    if year:
        rows.append(
            _annotation_row(
                doc_id=doc_id,
                company=company,
                question=f"{company}这份年度报告对应的报告年度是哪一年？",
                answer=year,
                page_index=1,
                evidence_text=_clip_text(first_page, "年度报告"),
                evidence_type="text",
                question_type="fact",
                difficulty="easy",
                source_section="cover",
                notes="v2_rule_generated; verify_manually",
            )
        )
    else:
        skipped.append("report_year")

    if title:
        rows.append(
            _annotation_row(
                doc_id=doc_id,
                company=company,
                question=f"{company}年度报告首页或标题处显示的报告标题是什么？",
                answer=title,
                page_index=1,
                evidence_text=_clip_text(first_page, "年度报告"),
                evidence_type="text",
                question_type="fact",
                difficulty="easy",
                source_section="cover",
                notes="v2_rule_generated; verify_manually",
            )
        )
    else:
        skipped.append("report_title")

    metric_specs = [
        ("营业收入", ["营业收入"], f"{company}{year or ''}年年度报告披露的营业收入是多少？", "main_accounting_data"),
        (
            "归属于上市公司股东的净利润",
            ["归属于上市公司股东的净利润"],
            f"{company}{year or ''}年年度报告披露的归属于上市公司股东的净利润是多少？",
            "main_accounting_data",
        ),
        (
            "经营活动产生的现金流量净额",
            ["经营活动产生的现金流量净额"],
            f"{company}{year or ''}年年度报告披露的经营活动产生的现金流量净额是多少？",
            "cash_flow",
        ),
        (
            "研发投入",
            ["研发投入", "研发费用"],
            f"{company}{year or ''}年年度报告披露的研发投入或研发费用是多少？",
            "r_and_d",
        ),
        (
            "资产总额",
            ["资产总额", "资产总计"],
            f"{company}{year or ''}年年度报告披露的资产总额是多少？",
            "balance_sheet",
        ),
    ]
    for metric_name, keywords, question, section in metric_specs:
        metric = _find_metric_answer(page_texts, keywords)
        if not metric:
            skipped.append(metric_name)
            continue
        answer_unit = str(metric.get("unit") or "")
        raw_value = str(metric["value"])
        answer = f"{raw_value} {answer_unit}".strip()
        rows.append(
            _annotation_row(
                doc_id=doc_id,
                company=company,
                question=question,
                answer=answer,
                page_index=int(metric["page_index"]),
                evidence_text=str(metric["value_evidence_text"]),
                evidence_type="numeric",
                question_type="numeric",
                difficulty="medium",
                source_section=section,
                notes="v2_rule_generated; numeric_value_need_verify_manually",
                answer_unit=answer_unit,
                raw_answer_value=raw_value,
                normalized_answer=answer,
                value_evidence_text=str(metric["value_evidence_text"]),
                unit_evidence_text=str(metric.get("unit_evidence_text") or ""),
            )
        )

    growth = _find_revenue_growth(page_texts)
    if growth:
        rows.append(
            _annotation_row(
                doc_id=doc_id,
                company=company,
                question=f"{company}{year or ''}年年度报告中营业收入相比上年的增减幅度是多少？",
                answer=str(growth["value"]),
                page_index=int(growth["page_index"]),
                evidence_text=str(growth["value_evidence_text"]),
                evidence_type="numeric",
                question_type="comparison",
                difficulty="medium",
                source_section="main_accounting_data",
                notes="v2_rule_generated; percentage_need_verify_manually",
                raw_answer_value=str(growth["value"]),
                normalized_answer=str(growth["value"]),
                value_evidence_text=str(growth["value_evidence_text"]),
            )
        )
    else:
        skipped.append("revenue_growth")

    risk = _find_risk_answer(page_texts)
    if risk:
        rows.append(
            _annotation_row(
                doc_id=doc_id,
                company=company,
                question=f"{company}年度报告中披露的风险相关内容是什么？",
                answer=str(risk["answer"]),
                page_index=int(risk["page_index"]),
                evidence_text=str(risk["value_evidence_text"]),
                evidence_type="text",
                question_type="risk_text",
                difficulty="medium",
                source_section="risk",
                notes="v2_rule_generated; verify_manually",
                normalized_answer=str(risk["answer"]),
                value_evidence_text=str(risk["value_evidence_text"]),
            )
        )
    else:
        skipped.append("risk_text")

    return rows[:questions_per_doc], skipped


def _annotation_row(
    *,
    doc_id: str,
    company: str,
    question: str,
    answer: str,
    page_index: int,
    evidence_text: str,
    evidence_type: str,
    question_type: str,
    difficulty: str,
    source_section: str,
    notes: str,
    answer_unit: str = "",
    raw_answer_value: str = "",
    normalized_answer: str = "",
    value_evidence_text: str = "",
    unit_evidence_text: str = "",
) -> dict[str, Any]:
    page_id = f"{doc_id}_p{page_index}"
    return {
        "query_id": "",
        "doc_id": doc_id,
        "question": question,
        "answer": answer,
        "evidence_pages": page_id,
        "evidence_text": evidence_text,
        "evidence_type": evidence_type,
        "is_answerable": "true",
        "notes": notes,
        "answer_unit": answer_unit,
        "raw_answer_value": raw_answer_value,
        "normalized_answer": normalized_answer or answer,
        "value_evidence_text": value_evidence_text or evidence_text,
        "unit_evidence_text": unit_evidence_text,
        "value_evidence_pages": page_id,
        "unit_evidence_pages": page_id if unit_evidence_text else "",
        "question_type": question_type,
        "difficulty": difficulty,
        "source_section": source_section,
        "company": company,
    }


def _company_name_from_doc_id(doc_id: str) -> str:
    return doc_id.split("：", 1)[0].strip() or doc_id


def _infer_report_year(doc_id: str, first_page: str) -> str:
    text = f"{doc_id} {first_page}"
    match = re.search(r"(20\d{2})\s*年\s*年度报告", text)
    if match:
        return match.group(1)
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else ""


def _infer_report_title(first_page: str, year: str) -> str:
    if year and f"{year} 年年度报告" in first_page:
        return f"{year} 年年度报告"
    if year and f"{year} 年度报告" in first_page:
        return f"{year} 年度报告"
    match = re.search(r"(20\d{2})\s*年\s*年度报告", first_page)
    if match:
        return f"{match.group(1)} 年年度报告"
    return ""


def _find_metric_answer(page_texts: list[str], keywords: list[str]) -> dict[str, Any] | None:
    for page_index, text in enumerate(page_texts, start=1):
        for keyword in keywords:
            start = text.find(keyword)
            if start < 0:
                continue
            after = text[start + len(keyword) : start + len(keyword) + 260]
            value_match = NUMBER_PATTERN.search(after)
            if not value_match:
                continue
            value = value_match.group(0)
            unit, unit_text = _find_unit_near(text, start)
            if not unit:
                unit, unit_text = _find_recent_unit(page_texts, page_index - 1)
            evidence = _clip_text(text, keyword, before=120, after=360)
            return {
                "page_index": page_index,
                "value": value,
                "unit": unit,
                "value_evidence_text": evidence,
                "unit_evidence_text": unit_text,
            }
    return None


def _find_revenue_growth(page_texts: list[str]) -> dict[str, Any] | None:
    for page_index, text in enumerate(page_texts, start=1):
        start = text.find("营业收入")
        if start < 0:
            continue
        window = text[start : start + 360]
        percentages = PERCENT_PATTERN.findall(window)
        if not percentages:
            continue
        return {
            "page_index": page_index,
            "value": percentages[0],
            "value_evidence_text": _clip_text(text, "营业收入", before=120, after=360),
        }
    return None


def _find_risk_answer(page_texts: list[str]) -> dict[str, Any] | None:
    risk_patterns = ["风险因素", "可能面对的风险", "公司面临的风险", "风险"]
    for page_index, text in enumerate(page_texts, start=1):
        if page_index < 8:
            continue
        for pattern in risk_patterns:
            position = text.find(pattern)
            if position < 0:
                continue
            evidence = _clip_text(text, pattern, before=40, after=320)
            answer = evidence[:180]
            return {"page_index": page_index, "answer": answer, "value_evidence_text": evidence}
    return None


def _find_unit_near(text: str, position: int) -> tuple[str, str]:
    window_start = max(0, position - 700)
    window = text[window_start : position + 120]
    matches = list(UNIT_PATTERN.finditer(window))
    if not matches:
        return "", ""
    match = matches[-1]
    unit = match.group(1)
    unit_text = _clip_text(window, match.group(0), before=80, after=120)
    return unit, unit_text


def _find_recent_unit(page_texts: list[str], current_page_zero_index: int) -> tuple[str, str]:
    for page_index in range(current_page_zero_index, max(-1, current_page_zero_index - 3), -1):
        if page_index < 0:
            continue
        matches = list(UNIT_PATTERN.finditer(page_texts[page_index]))
        if not matches:
            continue
        match = matches[-1]
        return match.group(1), _clip_text(page_texts[page_index], match.group(0), before=80, after=120)
    return "", ""


def _clip_text(text: str, needle: str, before: int = 80, after: int = 260) -> str:
    cleaned = _clean_text(text)
    position = cleaned.find(needle)
    if position < 0:
        return cleaned[: before + after].strip()
    start = max(0, position - before)
    end = min(len(cleaned), position + len(needle) + after)
    return cleaned[start:end].strip()


def _load_cn_queries(
    raw_dir: Path, dataset: str, nodes_by_page: dict[str, list[EvidenceNode]] | None = None
) -> list[QueryRecord]:
    # 这个函数的作用是从 CSV 或 Excel 文件中加载中文年报的问答标注数据，并将其转换为标准的 QueryRecord 对象列表，同时自动匹配证据节点
    candidates = [
        raw_dir / "qa_annotations_v2_reviewed.csv",
        raw_dir / "qa_annotations_v2_reviewed.xlsx",
        raw_dir / "qa_annotations_v2.csv",
        raw_dir / "qa_annotations_v2.xlsx",
        raw_dir / "qa_annotations.csv",
        raw_dir / "qa_annotations.xlsx",
    ]
    nodes_by_page = nodes_by_page or {}
    for candidate in candidates:
        if not candidate.exists():
            continue  # 文件不存在，跳过
        # 找到第一个存在的文件，读取并处理
        frame = pl.read_excel(candidate) if candidate.suffix == ".xlsx" else pl.read_csv(candidate)
        queries = []
        for idx, row in enumerate(frame.to_dicts(), start=1):  # 转换为字典列表并进行遍历
            doc_id = str(row.get("doc_id") or "")  # 提取 doc_id
            pages = str(row.get("evidence_pages") or "")  # 解析 evidence_pages
            evidence_page_ids = [item.strip() for item in pages.split(";") if item.strip()]  # 因为一个问题的证据可能分布在多个页面上，用分号分隔。
            evidence_node_ids, node_match_status = _match_cn_evidence_nodes(row, evidence_page_ids, nodes_by_page)
            metadata = {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "query_id",
                    "doc_id",
                    "question",
                    "answer",
                    "evidence_pages",
                    "is_answerable",
                }
            }
            metadata["annotation_file"] = candidate.name
            metadata["node_match_status"] = node_match_status
            queries.append(
                QueryRecord(
                    query_id=str(row.get("query_id") or f"cn_q{idx}"),
                    dataset=dataset,
                    doc_id=doc_id,
                    question=str(row.get("question") or ""),
                    answer=str(row.get("answer") or ""),
                    question_type=str(row.get("question_type") or row.get("evidence_type") or ""),
                    evidence_page_ids=evidence_page_ids,
                    evidence_node_ids=evidence_node_ids,
                    is_answerable=str(row.get("is_answerable", "true")).lower() not in {"false", "0", "no"},
                    metadata=metadata,
                )
            )
        return queries
    return []


def _match_cn_evidence_nodes(
    row: dict[str, Any],
    evidence_page_ids: list[str],
    nodes_by_page: dict[str, list[EvidenceNode]],
) -> tuple[list[str], str]:
    # 步骤 1：收集候选节点并评分
    scored: list[tuple[float, EvidenceNode]] = []
    for page_id in evidence_page_ids:  # 遍历 CSV 标注的页面
        for node in nodes_by_page.get(page_id, []):  # 获取该页面上的所有节点
            score = _score_node_for_annotation(row, node)  # 计算匹配分数
            if score > 0:
                scored.append((score, node))
    # 步骤 2：排序并选择 Top 3
    if scored:
        ordered = sorted(scored, key=lambda item: (-item[0], item[1].reading_order))  # 按分数倒序排序，如果分数相同则按阅读顺序排序
        node_ids = []
        for _, node in ordered[:3]:
            if node.node_id not in node_ids:
                node_ids.append(node.node_id)
        return node_ids, "matched"

    # 步骤 3：Fallback 策略（如果没找到匹配）
    # 如果没有评分 > 0 的节点
    fallback_ids = []
    for page_id in evidence_page_ids:
        nodes = nodes_by_page.get(page_id, [])
        if nodes:
            fallback_ids.append(nodes[0].node_id)  # 取每页的第一个节点
    return fallback_ids, "fallback" if fallback_ids else "missing"


def _score_node_for_annotation(row: dict[str, Any], node: EvidenceNode) -> float:
    text = _normalize_for_match(node.text)  # 节点文本（标准化后）
    score = 0.0  # 初始分数为 0
    # 从 CSV 行（row）中提取信息并标准化
    raw_value = _normalize_for_match(str(row.get("raw_answer_value") or ""))  # 原始数值
    answer = _normalize_for_match(str(row.get("answer") or ""))  # 最终答案
    question = str(row.get("question") or "")  # 问题原文
    value_evidence = _normalize_for_match(str(row.get("value_evidence_text") or ""))  # 数值证据片段
    unit_evidence = _normalize_for_match(str(row.get("unit_evidence_text") or ""))  # 单位证据片段
    evidence_text = _normalize_for_match(str(row.get("evidence_text") or ""))  # 通用证据文本

    for value in [raw_value, answer]:
        # 情况 A：精确匹配成功
        if value and value in text:
            score += 5.0
        # 情况 B：紧凑数值匹配成功
        compact = _compact_numeric_text(value)
        if compact and compact in _compact_numeric_text(text):
            score += 3.5
    # 检查问题和节点中是否同时出现了同一个财务关键词
    for keyword in FINANCIAL_KEYWORDS:
        if keyword in question and keyword in node.text:
            score += 4.0
    # 利用 CSV 中标注的“证据原文”进行匹配
    for snippet in [value_evidence, unit_evidence, evidence_text]:
        if len(snippet) >= 16 and snippet[:80] in text:
            score += 3.0
        elif snippet:
            score += _char_overlap_score(snippet, text)

    # 如果 CSV 中标注了单位（如"元"、"万元"），且该单位出现在节点文本中，加 1 分
    if str(row.get("answer_unit") or "") and str(row.get("answer_unit")) in node.text:
        score += 1.0
    return score


# _clean_text(text) - 基础清理 加 .replace(" ", "") - 去除所有空格
def _normalize_for_match(text: str) -> str:
    return _clean_text(text).replace(" ", "")

# 从一段文本中剔除所有“非数字”相关的字符，只保留数字、小数点、负号、括号和百分号
def _compact_numeric_text(text: str) -> str:
    return re.sub(r"[^0-9.\-()%]", "", text or "")


def _char_overlap_score(left: str, right: str) -> float:
    left_chars = set(left[:160])
    if not left_chars:
        return 0.0
    right_chars = set(right[:260])
    return min(2.0, len(left_chars & right_chars) / max(len(left_chars), 1) * 2.0)
