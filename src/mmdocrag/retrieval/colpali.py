from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from mmdocrag.paths import artifacts_root
from mmdocrag.schemas import PageRecord, QueryRecord, RetrievalHit


def resolve_page_image_path(page: PageRecord) -> Path:
    """Return a usable page image path or explain how to generate one."""
    if not page.page_image_path:
        raise FileNotFoundError(
            f"Page `{page.page_id}` has no page_image_path. Re-run `mdr prepare --dataset mmdocir` "
            "after downloading MMDocIR_pages.parquet with its image_binary column."
        )
    path = Path(page.page_image_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing page image for `{page.page_id}`: {path}. Re-run `mdr prepare --dataset mmdocir` "
            "on this machine so the page JPEGs are materialized under data/interim."
        )
    return path


def _safe_cache_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")


def _source_signature(path: Path, model_name: str) -> str:
    stat = path.stat()
    value = f"{model_name}\0{path.resolve()}\0{stat.st_size}\0{stat.st_mtime_ns}"
    return sha256(value.encode("utf-8")).hexdigest()


class ColPaliPageRetriever:
    """ColPali page encoder with on-disk CPU embedding caching."""

    def __init__(self, dataset: str, config: dict[str, Any]):
        self.dataset = dataset
        self.model_name = str(config.get("model", "vidore/colpali"))
        self.image_batch_size = int(config.get("image_batch_size", 1))
        self.query_batch_size = int(config.get("query_batch_size", 4))
        self.score_batch_size = int(config.get("score_batch_size", 8))
        self.use_cache = bool(config.get("use_embedding_cache", True))
        cache_value = config.get("embedding_cache_dir")
        self.cache_dir = (
            Path(str(cache_value)).expanduser()
            if cache_value
            else artifacts_root() / "colpali" / dataset / _safe_cache_name(self.model_name)
        )
        self._model: Any | None = None
        self._processor: Any | None = None
        self._torch: Any | None = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from colpali_engine.models import ColPali, ColPaliProcessor
            from colpali_engine.utils.torch_utils import get_torch_device
        except ImportError as exc:
            raise RuntimeError(
                "ColPali is optional. Install it on the CUDA machine with `uv sync --extra colpali` "
                "or `python -m pip install -e .[colpali]`."
            ) from exc

        device = get_torch_device("auto")
        if str(device) == "cpu":
            raise RuntimeError(
                "ColPali page retrieval requires CUDA or Apple MPS; CPU execution is disabled."
            )
        self._torch = torch
        self._model = ColPali.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map=device,
        ).eval()
        self._processor = ColPaliProcessor.from_pretrained(self.model_name)

    def _cache_path(self, page: PageRecord) -> Path:
        return self.cache_dir / f"{_safe_cache_name(page.page_id)}.pt"

    def _load_cached_embedding(self, page: PageRecord, image_path: Path) -> Any | None:
        if not self.use_cache:
            return None
        cache_path = self._cache_path(page)
        if not cache_path.exists():
            return None
        assert self._torch is not None
        payload = self._torch.load(cache_path, map_location="cpu", weights_only=True)
        if payload.get("source_signature") != _source_signature(image_path, self.model_name):
            return None
        return payload["embedding"]

    def _save_cached_embedding(self, page: PageRecord, image_path: Path, embedding: Any) -> None:
        if not self.use_cache:
            return
        assert self._torch is not None
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._torch.save(
            {
                "model_name": self.model_name,
                "source_signature": _source_signature(image_path, self.model_name),
                "embedding": embedding.cpu(),
            },
            self._cache_path(page),
        )

    def encode_pages(self, pages: list[PageRecord]) -> list[Any]:
        self._load_model()
        assert self._model is not None and self._processor is not None and self._torch is not None
        from PIL import Image

        embeddings: list[Any | None] = [None] * len(pages)
        pending: list[tuple[int, PageRecord, Path]] = []
        for index, page in enumerate(pages):
            image_path = resolve_page_image_path(page)
            cached = self._load_cached_embedding(page, image_path)
            if cached is None:
                pending.append((index, page, image_path))
            else:
                embeddings[index] = cached

        for start in range(0, len(pending), self.image_batch_size):
            batch_items = pending[start : start + self.image_batch_size]
            images = []
            for _, _, image_path in batch_items:
                with Image.open(image_path) as image:
                    images.append(image.convert("RGB"))
            batch = self._processor.process_images(images).to(self._model.device)
            with self._torch.inference_mode():
                batch_embeddings = self._model(**batch)
            for item, embedding in zip(batch_items, batch_embeddings, strict=True):
                index, page, image_path = item
                embedding = embedding.cpu()
                self._save_cached_embedding(page, image_path, embedding)
                embeddings[index] = embedding
            print(
                f"[mdr] ColPali encoded pages {start + len(batch_items)}/{len(pending)} (cache misses).",
                flush=True,
            )

        return [embedding for embedding in embeddings if embedding is not None]

    def encode_queries(self, queries: list[QueryRecord]) -> list[Any]:
        self._load_model()
        assert self._model is not None and self._processor is not None and self._torch is not None
        embeddings = []
        for start in range(0, len(queries), self.query_batch_size):
            batch_queries = queries[start : start + self.query_batch_size]
            batch = self._processor.process_queries([query.question for query in batch_queries]).to(
                self._model.device
            )
            with self._torch.inference_mode():
                embeddings.extend(embedding.cpu() for embedding in self._model(**batch))
        return embeddings

    def score(self, query_embeddings: list[Any], page_embeddings: list[Any]) -> Any:
        self._load_model()
        assert self._processor is not None
        return self._processor.score_multi_vector(
            query_embeddings,
            page_embeddings,
            batch_size=self.score_batch_size,
        )


def retrieve_colpali_pages(
    dataset: str,
    queries: list[QueryRecord],
    pages: list[PageRecord],
    top_k: int,
    config: dict[str, Any],
    search_scope: str,
) -> list[RetrievalHit]:
    retriever = ColPaliPageRetriever(dataset, config)
    page_embeddings = retriever.encode_pages(pages)
    query_embeddings = retriever.encode_queries(queries)
    page_indices_by_doc: dict[str, list[int]] = {}
    for index, page in enumerate(pages):
        page_indices_by_doc.setdefault(page.doc_id, []).append(index)

    hits: list[RetrievalHit] = []
    if search_scope == "corpus":
        score_rows = retriever.score(query_embeddings, page_embeddings)
        score_rows = list(score_rows)
        query_page_indices = [list(range(len(pages))) for _ in queries]
    else:
        score_rows = []
        query_page_indices = []
        for query_embedding, query in zip(query_embeddings, queries, strict=True):
            indices = page_indices_by_doc.get(query.doc_id, [])
            if not indices:
                raise ValueError(f"No pages found for query document `{query.doc_id}`.")
            score_rows.append(
                retriever.score([query_embedding], [page_embeddings[i] for i in indices])[0]
            )
            query_page_indices.append(indices)

    for query, scores, indices in zip(queries, score_rows, query_page_indices, strict=True):
        ranked = sorted(enumerate(scores.tolist()), key=lambda item: item[1], reverse=True)[:top_k]
        for rank, (local_index, score) in enumerate(ranked, start=1):
            page = pages[indices[local_index]]
            hits.append(
                RetrievalHit(
                    query_id=query.query_id,
                    rank=rank,
                    score=float(score),
                    doc_id=page.doc_id,
                    page_id=page.page_id,
                    text=page.page_text or page.ocr_text,
                    retriever="colpali_page",
                    metadata={
                        "model": retriever.model_name,
                        "page_image_path": page.page_image_path,
                    },
                )
            )
    return hits
