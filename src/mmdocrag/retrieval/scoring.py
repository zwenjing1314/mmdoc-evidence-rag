from __future__ import annotations

import math
import re
from collections import Counter, defaultdict


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", lowered)
    return tokens or [lowered.strip()] if lowered.strip() else []


class SimpleBM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.tokens = [tokenize(doc) for doc in docs]
        self.k1 = k1
        self.b = b
        self.doc_count = len(self.tokens)
        self.avgdl = sum(len(doc) for doc in self.tokens) / max(self.doc_count, 1)
        self.df: Counter[str] = Counter()
        for doc in self.tokens:
            self.df.update(set(doc))

    def score(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        scores = []
        for doc_tokens in self.tokens:
            tf = Counter(doc_tokens)
            doc_len = len(doc_tokens)
            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                df = self.df.get(token, 0)
                idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
                denom = tf[token] + self.k1 * (1 - self.b + self.b * doc_len / max(self.avgdl, 1e-9))
                score += idf * tf[token] * (self.k1 + 1) / denom
            scores.append(score)
        return scores


class SimpleTfidf:
    def __init__(self, docs: list[str]):
        self.docs = [tokenize(doc) for doc in docs]
        self.doc_count = len(self.docs)
        self.df: Counter[str] = Counter()
        for doc in self.docs:
            self.df.update(set(doc))
        self.vectors = [self._vector(doc) for doc in self.docs]

    def _idf(self, token: str) -> float:
        return math.log((self.doc_count + 1) / (self.df.get(token, 0) + 1)) + 1

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = max(sum(counts.values()), 1)
        return {token: count / total * self._idf(token) for token, count in counts.items()}

    def score(self, query: str) -> list[float]:
        query_vector = self._vector(tokenize(query))
        return [cosine(query_vector, doc_vector) for doc_vector in self.vectors]


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(value * right.get(token, 0.0) for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return dict(scores)
