"""RAG (retrieval-augmented generation) tool for ChemAgent.

Indexes a corpus of plain-text documents in `corpus/` and exposes a
`rag_search(query, k)` tool that returns the top-k most relevant chunks
with their source citation. Uses BM25 (Okapi) — no ML dependencies, no
embeddings, no network. Sufficient for keyword-heavy domain queries
("RAFT chain transfer constant", "Müller dispersity equation", etc.).

Corpus convention
-----------------
- Files in CORPUS_DIR with extensions .txt, .md
- Each file is split into ~500-char overlapping chunks
- Chunk citation format: "<filename> · chunk <i>"

Limitations
-----------
- Pure lexical match — no semantic similarity. Won't find "polymer mass"
  if the corpus only says "molecular weight". Future: replace BM25 with
  embedding similarity (sentence-transformers) once dependencies allow.
- No persistence yet — index is rebuilt in-memory on first call. Cached
  for subsequent calls in the same process.
"""
import math
import re
from pathlib import Path
from typing import Iterable


CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus"
CHUNK_SIZE = 500       # characters
CHUNK_OVERLAP = 100    # characters
BM25_K1 = 1.5
BM25_B = 0.75

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop very short tokens."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1]


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping fixed-size chunks. Tries to break on whitespace."""
    chunks = []
    n = len(text)
    if n <= size:
        return [text.strip()] if text.strip() else []
    start = 0
    while start < n:
        end = min(start + size, n)
        # try to extend to next whitespace for cleaner break
        if end < n:
            ws = text.rfind(" ", start, end + 50)
            if ws > start + size // 2:
                end = ws
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - overlap if end - overlap > start else end
    return chunks


class _BM25Index:
    """Minimal Okapi BM25 implementation. Pure-Python, no deps."""

    def __init__(self, docs: list[list[str]]) -> None:
        self.docs = docs
        self.N = len(docs)
        self.doc_lens = [len(d) for d in docs]
        self.avgdl = sum(self.doc_lens) / self.N if self.N else 0.0

        # Document frequency
        self.df: dict[str, int] = {}
        for doc in docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

        # Inverse document frequency (BM25+ form, always >= 0)
        self.idf: dict[str, float] = {}
        for term, df in self.df.items():
            self.idf[term] = math.log(1 + (self.N - df + 0.5) / (df + 0.5))

        # Term frequency per doc
        self.tf: list[dict[str, int]] = []
        for doc in docs:
            tf: dict[str, int] = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            self.tf.append(tf)

    def score(self, query_terms: Iterable[str], doc_idx: int) -> float:
        score = 0.0
        dl = self.doc_lens[doc_idx]
        tf = self.tf[doc_idx]
        for term in query_terms:
            if term not in tf:
                continue
            idf = self.idf.get(term, 0.0)
            f = tf[term]
            denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / (self.avgdl or 1))
            score += idf * (f * (BM25_K1 + 1)) / denom
        return score

    def rank(self, query_terms: list[str], k: int) -> list[tuple[int, float]]:
        scores = [(i, self.score(query_terms, i)) for i in range(self.N)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in scores[:k] if s > 0]


# Module-level cache, built lazily on first call
_INDEX: _BM25Index | None = None
_CHUNKS: list[dict] | None = None


def _build_index(corpus_dir: Path | str = CORPUS_DIR) -> tuple[_BM25Index, list[dict]]:
    """Read corpus files, chunk them, build BM25 index."""
    cdir = Path(corpus_dir)
    chunks: list[dict] = []
    if cdir.exists():
        for fp in sorted(cdir.iterdir()):
            if fp.suffix.lower() not in {".txt", ".md"}:
                continue
            text = fp.read_text(encoding="utf-8")
            for i, chunk_text in enumerate(_chunk_text(text)):
                chunks.append({
                    "source": fp.name,
                    "chunk_idx": i,
                    "text": chunk_text,
                })
    tokenised = [_tokenize(c["text"]) for c in chunks]
    return _BM25Index(tokenised), chunks


def _ensure_index(corpus_dir: Path | str | None = None) -> tuple[_BM25Index, list[dict]]:
    global _INDEX, _CHUNKS
    if corpus_dir is not None:
        # Forced rebuild for a custom corpus (e.g. tests)
        return _build_index(corpus_dir)
    if _INDEX is None or _CHUNKS is None:
        _INDEX, _CHUNKS = _build_index()
    return _INDEX, _CHUNKS


def rag_search(query: str, k: int = 3) -> dict:
    """Retrieve top-k corpus chunks relevant to the query.

    Parameters
    ----------
    query : str   Free-text query, e.g. "RAFT chain transfer constant"
    k : int       How many results (default 3, max 10)

    Returns
    -------
    dict with:
      query, results: list of {source, chunk_idx, score, text}
      n_corpus_chunks: total chunks in the corpus
    """
    if not query or not query.strip():
        return {"error": "Empty query"}
    if k < 1 or k > 10:
        return {"error": "k must be between 1 and 10"}

    index, chunks = _ensure_index()
    if not chunks:
        return {
            "error": (
                f"Corpus is empty. Add .txt or .md files to {CORPUS_DIR} "
                "to enable retrieval."
            )
        }

    q_tokens = _tokenize(query)
    if not q_tokens:
        return {"error": "Query produced no usable tokens"}

    ranked = index.rank(q_tokens, k)
    results = []
    for doc_idx, score in ranked:
        c = chunks[doc_idx]
        results.append({
            "source": c["source"],
            "chunk_idx": c["chunk_idx"],
            "score": round(score, 4),
            "text": c["text"],
        })
    return {
        "query": query,
        "n_corpus_chunks": len(chunks),
        "results": results,
    }


def rebuild_index(corpus_dir: Path | str | None = None) -> dict:
    """Force rebuild of the corpus index. Useful after editing corpus files."""
    global _INDEX, _CHUNKS
    _INDEX, _CHUNKS = _build_index(corpus_dir or CORPUS_DIR)
    return {
        "corpus_dir": str(corpus_dir or CORPUS_DIR),
        "n_chunks": len(_CHUNKS),
        "n_unique_terms": len(_INDEX.df) if _INDEX else 0,
    }
