"""Export one MMDocIR document from parquet into a human-readable folder.

The MMDocIR parquet files store JPEG bytes in ``image_binary`` columns.  This
script writes those bytes back to JPEG files and exports the accompanying text,
layout type, and bounding-box metadata without modifying the source dataset.

python scripts\export_mmdocir_document.py `
   --doc-index 0 `
   --output-dir artifacts\exports\mmdocir
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import polars as pl


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "document"


def as_bytes(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    return bytes(value)


def write_text(path: Path, value: Any) -> None:
    path.write_text(str(value or ""), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/raw/mmdocir_evaluation"),
        help="Directory containing MMDocIR_annotations.jsonl and parquet files.",
    )
    parser.add_argument(
        "--doc-name",
        help="Exact doc_name from MMDocIR_pages.parquet (for example 2310.05634v2).",
    )
    parser.add_argument(
        "--doc-index",
        type=int,
        help="Zero-based document index when --doc-name is omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/exports/mmdocir"),
        help="Parent directory for exported document folders.",
    )
    return parser.parse_args()


def choose_document(pages_path: Path, doc_name: str | None, doc_index: int | None) -> str:
    names = (
        pl.scan_parquet(pages_path)
        .select("doc_name")
        .unique()
        .sort("doc_name")
        .collect()
        .get_column("doc_name")
        .to_list()
    )
    if doc_name is not None:
        if doc_name not in names:
            preview = ", ".join(str(name) for name in names[:10])
            raise ValueError(f"Unknown doc_name: {doc_name}. First available names: {preview}")
        return doc_name
    index = 0 if doc_index is None else doc_index
    if index < 0 or index >= len(names):
        raise ValueError(f"--doc-index must be between 0 and {len(names) - 1}.")
    return str(names[index])


def export_document(data_root: Path, doc_name: str, output_dir: Path) -> Path:
    pages_path = data_root / "MMDocIR_pages.parquet"
    layouts_path = data_root / "MMDocIR_layouts.parquet"
    required = [pages_path, layouts_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing MMDocIR files: " + ", ".join(missing))

    page_columns = [
        "doc_name",
        "domain",
        "passage_id",
        "image_path",
        "image_binary",
        "ocr_text",
        "vlm_text",
    ]
    layout_columns = [
        "doc_name",
        "type",
        "layout_id",
        "page_id",
        "image_path",
        "image_binary",
        "text",
        "ocr_text",
        "vlm_text",
        "bbox",
        "page_size",
    ]
    pages = (
        pl.scan_parquet(pages_path)
        .filter(pl.col("doc_name") == doc_name)
        .select(page_columns)
        .sort("passage_id")
        .collect()
        .to_dicts()
    )
    layouts = (
        pl.scan_parquet(layouts_path)
        .filter(pl.col("doc_name") == doc_name)
        .select(layout_columns)
        .sort(["page_id", "layout_id"])
        .collect()
        .to_dicts()
    )
    if not pages:
        raise ValueError(f"No pages found for {doc_name!r}.")

    destination = output_dir / safe_name(Path(doc_name).stem)
    page_image_dir = destination / "pages"
    layout_image_dir = destination / "layouts"
    page_text_dir = destination / "page_text"
    layout_text_dir = destination / "layout_text"
    for directory in (page_image_dir, layout_image_dir, page_text_dir, layout_text_dir):
        directory.mkdir(parents=True, exist_ok=True)

    page_records = []
    for row in pages:
        page_id = int(row["passage_id"])
        image_file = page_image_dir / f"page_{page_id:04d}.jpg"
        image_bytes = as_bytes(row.get("image_binary"))
        if image_bytes:
            image_file.write_bytes(image_bytes)
        write_text(page_text_dir / f"page_{page_id:04d}.txt", row.get("ocr_text") or row.get("vlm_text"))
        page_records.append(
            {
                "page_id": page_id,
                "image": str(image_file.relative_to(destination)) if image_file.exists() else None,
                "source_image_path": row.get("image_path"),
                "domain": row.get("domain"),
                "ocr_text_file": str((page_text_dir / f"page_{page_id:04d}.txt").relative_to(destination)),
                "vlm_text": row.get("vlm_text") or "",
            }
        )

    layout_records = []
    for row in layouts:
        page_id = int(row["page_id"])
        layout_id = int(row["layout_id"])
        stem = f"page_{page_id:04d}_layout_{layout_id:06d}"
        image_file = layout_image_dir / f"{stem}.jpg"
        image_bytes = as_bytes(row.get("image_binary"))
        if image_bytes:
            image_file.write_bytes(image_bytes)
        text_file = layout_text_dir / f"{stem}.txt"
        write_text(text_file, row.get("text") or row.get("ocr_text") or row.get("vlm_text"))
        layout_records.append(
            {
                "page_id": page_id,
                "layout_id": layout_id,
                "type": row.get("type"),
                "bbox": row.get("bbox"),
                "page_size": row.get("page_size"),
                "image": str(image_file.relative_to(destination)) if image_file.exists() else None,
                "source_image_path": row.get("image_path"),
                "text_file": str(text_file.relative_to(destination)),
                "ocr_text": row.get("ocr_text") or "",
                "vlm_text": row.get("vlm_text") or "",
            }
        )

    (destination / "pages.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in page_records), encoding="utf-8"
    )
    (destination / "layouts.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in layout_records), encoding="utf-8"
    )
    manifest = {
        "doc_name": doc_name,
        "pages": len(page_records),
        "layouts": len(layout_records),
        "page_images": sum(row["image"] is not None for row in page_records),
        "layout_images": sum(row["image"] is not None for row in layout_records),
        "source": {"pages": str(pages_path), "layouts": str(layouts_path)},
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# {doc_name}",
        "",
        f"- Pages: {len(page_records)}",
        f"- Layouts: {len(layout_records)}",
        "",
        "## Pages",
        "",
    ]
    for row in page_records:
        image = row["image"] or "(image_binary missing)"
        lines.extend([f"### Page {row['page_id']}", "", f"![page {row['page_id']}]({image})", ""])
    lines.extend(["## Layouts", "", "See `layouts.jsonl` and the `layouts/` folder for all layout images and bbox metadata.", ""])
    (destination / "document.md").write_text("\n".join(lines), encoding="utf-8")
    return destination


def main() -> None:
    args = parse_args()
    pages_path = args.data_root / "MMDocIR_pages.parquet"
    doc_name = choose_document(pages_path, args.doc_name, args.doc_index)
    destination = export_document(args.data_root, doc_name, args.output_dir)
    print(f"Exported {doc_name} to {destination}")


if __name__ == "__main__":
    main()
