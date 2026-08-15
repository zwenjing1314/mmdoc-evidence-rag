from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from mmdocrag.evaluation.metrics import group_hits, region_hit_at_k
from mmdocrag.evaluation.pipeline import load_run_queries, resolve_run_dir
from mmdocrag.io import read_hits
from mmdocrag.retrieval.pipeline import METRIC_ALIASES, query_target_slots, text_has_unit
from mmdocrag.schemas import QueryRecord, RetrievalHit


@dataclass(frozen=True)
class SufficiencyResult:
    query_id: str
    status: str
    covered_items: list[str]
    missing_items: list[str]
    metric_ok: bool
    year_ok: bool
    unit_ok: bool
    value_ok: bool
    citation_ok: bool
    coverage_ratio: float
    evidence_node_ids: list[str]
    evidence_pages: list[str]
    evidence_text: str


def verify_evidence_run(run: Path, top_k: int = 3) -> dict[str, float]:
    run_dir = resolve_run_dir(run)
    run_info = json.loads((run_dir / "run_info.json").read_text(encoding="utf-8"))
    queries = load_run_queries(run_dir, run_info)
    hits = read_hits(run_dir / "predictions.parquet")
    results = verify_evidence_sufficiency(queries, hits, top_k=top_k)
    metrics = sufficiency_metrics(queries, hits, results, top_k=top_k)

    write_sufficiency_cases(run_dir / "evidence_sufficiency_cases.csv", results)
    (run_dir / "evidence_sufficiency_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_sufficiency_summary(
        run_dir / "evidence_sufficiency_summary.md", run_info, metrics, results, top_k
    )
    return metrics


def verify_evidence_sufficiency(
    queries: list[QueryRecord],
    hits: list[RetrievalHit],
    top_k: int = 3,
) -> list[SufficiencyResult]:
    grouped = group_hits(hits)
    results: list[SufficiencyResult] = []
    for query in queries:
        evidence_hits = grouped.get(query.query_id, [])[:top_k]
        evidence_text = "\n".join(hit.text for hit in evidence_hits)
        evidence_node_ids = [hit.node_id or "" for hit in evidence_hits if hit.node_id]
        evidence_pages = [hit.page_id for hit in evidence_hits]
        check = check_query_evidence(query, evidence_text, evidence_node_ids)
        citation_ok = bool(set(evidence_node_ids).intersection(query.evidence_node_ids))
        status = decide_sufficiency_status(check, citation_ok)
        results.append(
            SufficiencyResult(
                query_id=query.query_id,
                status=status,
                covered_items=check["covered_items"],
                missing_items=check["missing_items"],
                metric_ok=check["metric_ok"],
                year_ok=check["year_ok"],
                unit_ok=check["unit_ok"],
                value_ok=check["value_ok"],
                citation_ok=citation_ok,
                coverage_ratio=check["coverage_ratio"],
                evidence_node_ids=evidence_node_ids,
                evidence_pages=evidence_pages,
                evidence_text=evidence_text,
            )
        )
    return results


def check_query_evidence(
    query: QueryRecord,
    evidence_text: str,
    evidence_node_ids: list[str],
) -> dict[str, Any]:
    normalized_text = normalize_compact(evidence_text)
    required_items = required_evidence_items(query)
    covered_items: list[str] = []
    missing_items: list[str] = []

    metric_ok = check_metric(query, normalized_text)
    year_ok = check_year(query, normalized_text)
    unit_ok = check_unit(query, normalized_text)
    value_ok = check_value(query, normalized_text)
    item_checks = {
        "metric": metric_ok,
        "year": year_ok,
        "unit": unit_ok,
        "value": value_ok,
    }
    for item in required_items:
        if item_checks[item]:
            covered_items.append(item)
        else:
            missing_items.append(item)

    # 文本型问题没有稳定四元组时，用检索到的 gold node 与覆盖槽位共同判断。
    if not required_items:
        target_slots = query_target_slots(query)
        covered_slots = covered_target_slots(target_slots, normalized_text)
        covered_items = sorted(covered_slots)
        missing_items = sorted(target_slots - covered_slots)
        if not target_slots and evidence_node_ids:
            covered_items = ["evidence_present"]

    denominator = len(covered_items) + len(missing_items)
    coverage_ratio = len(covered_items) / denominator if denominator else 0.0
    return {
        "covered_items": covered_items,
        "missing_items": missing_items,
        "metric_ok": metric_ok,
        "year_ok": year_ok,
        "unit_ok": unit_ok,
        "value_ok": value_ok,
        "coverage_ratio": coverage_ratio,
    }


def decide_sufficiency_status(check: dict[str, Any], citation_ok: bool) -> str:
    missing = set(check["missing_items"])
    coverage_ratio = float(check["coverage_ratio"])
    if not missing and citation_ok:
        return "sufficient"
    if not missing and not citation_ok:
        return "citation_mismatch"
    if coverage_ratio >= 0.5:
        return "partial"
    return "insufficient"


def required_evidence_items(query: QueryRecord) -> list[str]:
    items: list[str] = []
    if query.question_type in {"numeric", "comparison"} and query_has_metric(query):
        items.append("metric")
    if query.question_type in {"numeric", "comparison"} and extract_query_years(query):
        items.append("year")
    if query.question_type in {"numeric", "comparison"} and (
        query.metadata.get("answer_unit") or answer_has_unit(query.answer)
    ):
        items.append("unit")
    if query.metadata.get("raw_answer_value") or answer_has_number(query.answer):
        items.append("value")
    return items


def query_has_metric(query: QueryRecord) -> bool:
    text = normalize_compact(query.question)
    return any(any(alias in text for alias in aliases) for aliases in METRIC_ALIASES.values())


def check_metric(query: QueryRecord, normalized_text: str) -> bool:
    question = normalize_compact(query.question)
    matched_metrics = [
        metric
        for metric, aliases in METRIC_ALIASES.items()
        if any(alias in question for alias in aliases)
    ]
    if not matched_metrics:
        return False
    return any(
        alias in normalized_text
        for metric in matched_metrics
        for alias in METRIC_ALIASES.get(metric, ())
    )


def check_year(query: QueryRecord, normalized_text: str) -> bool:
    years = extract_query_years(query)
    if not years:
        return False
    return any(year in normalized_text for year in years)


def check_unit(query: QueryRecord, normalized_text: str) -> bool:
    unit = query.metadata.get("answer_unit") or extract_answer_unit(query.answer)
    if not unit:
        return False
    return text_has_unit(normalized_text, str(unit))


def check_value(query: QueryRecord, normalized_text: str) -> bool:
    raw_value = str(query.metadata.get("raw_answer_value") or extract_answer_value(query.answer))
    if not raw_value:
        return False
    return value_in_text(raw_value, normalized_text)


def covered_target_slots(target_slots: set[str], normalized_text: str) -> set[str]:
    covered: set[str] = set()
    for slot in target_slots:
        if slot.startswith("metric:"):
            metric = slot.removeprefix("metric:")
            if any(alias in normalized_text for alias in METRIC_ALIASES.get(metric, ())):
                covered.add(slot)
        elif slot_is_covered(slot, normalized_text):
            covered.add(slot)
    return covered


def slot_is_covered(slot: str, normalized_text: str) -> bool:
    return (
        (slot.startswith("year:") and slot.removeprefix("year:") in normalized_text)
        or (slot.startswith("unit:") and text_has_unit(normalized_text, slot.removeprefix("unit:")))
        or (slot.startswith("keyword:") and slot.removeprefix("keyword:") in normalized_text)
        or (slot == "numeric_shape" and answer_has_number(normalized_text))
    )


def sufficiency_metrics(
    queries: list[QueryRecord],
    hits: list[RetrievalHit],
    results: list[SufficiencyResult],
    top_k: int,
) -> dict[str, float]:
    total = len(results)
    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
    sufficient = status_counts.get("sufficient", 0)
    citation_mismatch = status_counts.get("citation_mismatch", 0)
    partial = status_counts.get("partial", 0)
    avg_coverage = sum(result.coverage_ratio for result in results) / total if total else 0.0
    return {
        "top_k": float(top_k),
        "queries": float(total),
        "sufficiency_rate": sufficient / total if total else 0.0,
        "partial_or_sufficient_rate": (sufficient + partial) / total if total else 0.0,
        "citation_mismatch_rate": citation_mismatch / total if total else 0.0,
        "avg_required_item_coverage": avg_coverage,
        "region_hit@k": region_hit_at_k(queries, hits, top_k),
        **{f"status_{key}": float(value) for key, value in sorted(status_counts.items())},
    }


def write_sufficiency_cases(path: Path, results: list[SufficiencyResult]) -> None:
    rows = [
        {
            "query_id": result.query_id,
            "status": result.status,
            "covered_items": ";".join(result.covered_items),
            "missing_items": ";".join(result.missing_items),
            "metric_ok": result.metric_ok,
            "year_ok": result.year_ok,
            "unit_ok": result.unit_ok,
            "value_ok": result.value_ok,
            "citation_ok": result.citation_ok,
            "coverage_ratio": result.coverage_ratio,
            "evidence_node_ids": ";".join(result.evidence_node_ids),
            "evidence_pages": ";".join(result.evidence_pages),
            "evidence_text": result.evidence_text[:1200],
        }
        for result in results
    ]
    pl.DataFrame(rows).write_csv(path)


def write_sufficiency_summary(
    path: Path,
    run_info: dict[str, Any],
    metrics: dict[str, float],
    results: list[SufficiencyResult],
    top_k: int,
) -> None:
    lines = [
        f"# {run_info['experiment_name']} Evidence Sufficiency Summary",
        "",
        f"- Dataset: `{run_info['dataset']}`",
        f"- Retriever: `{run_info['retriever_type']}`",
        f"- Evidence TopK: `{top_k}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value:.4f} |")
    lines.extend(["", "## Example Insufficient Cases", ""])
    for result in [item for item in results if item.status != "sufficient"][:8]:
        lines.append(f"### {result.query_id}")
        lines.append("")
        lines.append(f"- Status: `{result.status}`")
        lines.append(f"- Covered: `{', '.join(result.covered_items) or '-'}`")
        lines.append(f"- Missing: `{', '.join(result.missing_items) or '-'}`")
        lines.append(f"- Citation OK: `{result.citation_ok}`")
        lines.append(f"- Evidence nodes: `{', '.join(result.evidence_node_ids) or '-'}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def extract_query_years(query: QueryRecord) -> set[str]:
    return set(re.findall(r"20\d{2}", query.question))


def answer_has_unit(answer: str) -> bool:
    return bool(re.search(r"(人民币)?(元|万元|亿元)|%|百分点", answer))


def extract_answer_unit(answer: str) -> str:
    match = re.search(r"(人民币元|人民币万元|人民币亿元|万元|亿元|元|%|百分点)", answer)
    return match.group(1) if match else ""


def answer_has_number(answer: str) -> bool:
    return bool(re.search(r"[-+]?\(?\d[\d,]*(?:\.\d+)?\)?%?", answer))


def extract_answer_value(answer: str) -> str:
    match = re.search(r"[-+]?\(?\d[\d,]*(?:\.\d+)?\)?%?", answer)
    return match.group(0) if match else ""


def value_in_text(raw_value: str, normalized_text: str) -> bool:
    candidates = normalized_value_candidates(raw_value)
    compact_text = re.sub(r"[,\s]", "", normalized_text)
    if any(candidate and candidate in compact_text for candidate in candidates):
        return True
    normalized_numbers = {normalize_number(match) for match in number_like_tokens(normalized_text)}
    return bool(candidates.intersection(normalized_numbers))


def normalized_value_candidates(raw_value: str) -> set[str]:
    compact = normalize_number(raw_value)
    candidates = {compact}
    if compact.startswith("-"):
        candidates.add(compact[1:])
    return {candidate for candidate in candidates if candidate}


def number_like_tokens(text: str) -> list[str]:
    return re.findall(r"[-+]?[(（]?\d[\d,]*(?:\.\d+)?[)）]?%?", text)


def normalize_number(value: str) -> str:
    value = value.strip()
    negative = value.startswith("-") or (
        (value.startswith("(") and value.endswith(")"))
        or (value.startswith("（") and value.endswith("）"))
    )
    value = value.strip("()（）")
    value = value.replace(",", "").replace("%", "")
    value = re.sub(r"[^0-9.\-]", "", value)
    value = value.lstrip("+")
    if negative and value and not value.startswith("-"):
        value = f"-{value}"
    return value


def normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
