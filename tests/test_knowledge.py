"""Unit tests for the RAG / knowledge tool."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.knowledge import (
    _BM25Index,
    _chunk_text,
    _tokenize,
    rag_search,
    rebuild_index,
)


class TestTokenize:
    def test_lowercases(self):
        assert _tokenize("HELLO World") == ["hello", "world"]

    def test_drops_punctuation(self):
        assert _tokenize("Mn = Mw / Do.") == ["mn", "mw", "do"]

    def test_keeps_numbers(self):
        toks = _tokenize("kp = 480 L/mol/s")
        assert "kp" in toks
        assert "480" in toks


class TestChunkText:
    def test_short_text_one_chunk(self):
        chunks = _chunk_text("hello world", size=500)
        assert chunks == ["hello world"]

    def test_long_text_splits(self):
        text = "word " * 300  # 1500 chars
        chunks = _chunk_text(text, size=500, overlap=50)
        assert len(chunks) >= 3
        # adjacent chunks should overlap
        assert chunks[0][-20:] in chunks[1] or len(chunks[1]) >= 20

    def test_empty_text(self):
        assert _chunk_text("") == []


class TestBM25:
    def test_finds_relevant_doc(self):
        docs = [
            ["the", "raft", "polymerization", "uses", "a", "chain", "transfer", "agent"],
            ["antimicrobial", "peptides", "are", "cationic", "and", "amphipathic"],
            ["dispersity", "is", "the", "ratio", "mw", "over", "mn"],
        ]
        idx = _BM25Index(docs)
        ranked = idx.rank(["raft", "polymerization"], k=3)
        # raft doc (idx 0) should rank highest
        assert ranked[0][0] == 0
        assert ranked[0][1] > 0

    def test_empty_query_returns_no_score(self):
        idx = _BM25Index([["a", "b", "c"]])
        ranked = idx.rank([], k=1)
        assert ranked == []

    def test_no_matching_term(self):
        idx = _BM25Index([["alpha", "beta"]])
        ranked = idx.rank(["zeta"], k=1)
        assert ranked == []  # zero score filtered out


class TestRagSearch:
    def setup_method(self):
        # Use the real corpus for these tests
        rebuild_index()

    def test_finds_raft_content(self):
        r = rag_search("RAFT chain transfer constant CDB", k=3)
        assert "error" not in r
        assert r["n_corpus_chunks"] > 0
        assert len(r["results"]) > 0
        top = r["results"][0]
        assert "raft" in top["text"].lower() or "cdb" in top["text"].lower()
        assert top["source"]
        assert top["score"] > 0

    def test_finds_amp_content(self):
        r = rag_search("antimicrobial peptide charge hydrophobic moment", k=3)
        assert "error" not in r
        top_text = " ".join(x["text"].lower() for x in r["results"])
        assert "antimicrobial" in top_text or "hydrophobic" in top_text

    def test_finds_snapps_content(self):
        r = rag_search("SNAPPs star polymer Qiao", k=2)
        assert "error" not in r
        assert any("snapp" in x["text"].lower() for x in r["results"])

    def test_finds_dispersity_content(self):
        r = rag_search("Mueller equation dispersity Mw Mn", k=2)
        assert "error" not in r
        assert any("dispersity" in x["text"].lower() or "mueller" in x["text"].lower()
                   for x in r["results"])

    def test_empty_query(self):
        r = rag_search("", k=3)
        assert "error" in r

    def test_invalid_k(self):
        r = rag_search("raft", k=0)
        assert "error" in r
        r = rag_search("raft", k=20)
        assert "error" in r

    def test_results_have_citation(self):
        r = rag_search("RAFT", k=2)
        for res in r["results"]:
            assert "source" in res
            assert "chunk_idx" in res
            assert "score" in res
            assert "text" in res


class TestRebuildIndex:
    def test_returns_stats(self):
        stats = rebuild_index()
        assert stats["n_chunks"] > 0
        assert stats["n_unique_terms"] > 0
        assert "corpus_dir" in stats
