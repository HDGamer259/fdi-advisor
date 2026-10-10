"""Embedding TF-IDF (unigram + bigram, không dấu) & retriever có ngưỡng chặn.

Nhẹ, deterministic, không cần API key -> chạy tốt trên Streamlit Cloud/Render.
Có thể thay bằng embedding neural (sentence-transformers / Gemini) qua cùng interface.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .text_utils import tokenize


def _features(tokens: list[str]) -> list[str]:
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]


class TfidfEmbedder:
    def __init__(self) -> None:
        self.idf: dict[str, float] = {}

    def fit(self, docs: list[str]) -> "TfidfEmbedder":
        n = len(docs)
        df: Counter = Counter()
        for d in docs:
            df.update(set(_features(tokenize(d))))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        return self

    def embed(self, text: str) -> dict[str, float]:
        tf = Counter(_features(tokenize(text)))
        vec = {t: c * self.idf[t] for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


@dataclass(frozen=True)
class Chunk:
    province_id: str
    field: str
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float      # cosine similarity
    coverage: float   # tỷ lệ (trọng số idf) token query xuất hiện trong chunk


class Retriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.embedder = TfidfEmbedder().fit([c.text for c in chunks])
        self.vectors = [self.embedder.embed(c.text) for c in chunks]
        self.token_sets = [set(tokenize(c.text)) for c in chunks]
        self.token_df: Counter = Counter(t for s in self.token_sets for t in s)

    def search(
        self,
        query_tokens: list[str],
        province_ids: set[str] | None = None,
        top_k: int = 2,
        min_coverage: float = 0.6,
    ) -> list[Hit]:
        """Chỉ trả hit khi đa số token query (theo idf) thực sự có trong chunk."""
        if not query_tokens:
            return []
        qvec = self.embedder.embed(" ".join(query_tokens))
        q_weights = {t: self.embedder.idf.get(t, 1.0) for t in set(query_tokens)}
        total = sum(q_weights.values()) or 1.0
        hits: list[Hit] = []
        for chunk, vec, toks in zip(self.chunks, self.vectors, self.token_sets):
            if province_ids and chunk.province_id not in province_ids:
                continue
            coverage = sum(w for t, w in q_weights.items() if t in toks) / total
            if coverage < min_coverage:
                continue
            hits.append(Hit(chunk, cosine(qvec, vec), coverage))
        hits.sort(key=lambda h: (h.coverage, h.score), reverse=True)
        return hits[:top_k]
