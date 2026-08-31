from __future__ import annotations

import pytest

from mmdocrag.retrieval.colpali import resolve_page_image_path
from mmdocrag.schemas import PageRecord


def test_colpali_requires_materialized_page_image(tmp_path):
    page = PageRecord(doc_id="doc", page_id="doc_p0", page_index=1)
    with pytest.raises(FileNotFoundError, match="no page_image_path"):
        resolve_page_image_path(page)

    missing = PageRecord(
        doc_id="doc",
        page_id="doc_p0",
        page_index=1,
        page_image_path=str(tmp_path / "missing.jpg"),
    )
    with pytest.raises(FileNotFoundError, match="Missing page image"):
        resolve_page_image_path(missing)


def test_colpali_uses_existing_page_image(tmp_path):
    image_path = tmp_path / "page.jpg"
    image_path.write_bytes(b"placeholder")
    page = PageRecord(
        doc_id="doc",
        page_id="doc_p0",
        page_index=1,
        page_image_path=str(image_path),
    )
    assert resolve_page_image_path(page) == image_path
