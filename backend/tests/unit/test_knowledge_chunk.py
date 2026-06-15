from src.modules.knowledge.service import chunk_text


def test_chunk_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_small_single():
    assert chunk_text("texto curto") == ["texto curto"]


def test_chunk_overlap_and_coverage():
    text = "x" * 3000
    chunks = chunk_text(text, size=1000, overlap=100)
    assert len(chunks) >= 3
    # cada chunk respeita o tamanho máximo
    assert all(len(c) <= 1000 for c in chunks)
    # cobre todo o conteúdo
    assert sum(len(c) for c in chunks) >= len(text)
