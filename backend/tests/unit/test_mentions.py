from src.modules.chat.service import MENTION_RE


def test_extracts_mentions():
    assert MENTION_RE.findall("oi @Vendinha e @Bitzao, tudo bem?") == ["Vendinha", "Bitzao"]


def test_no_mentions():
    assert MENTION_RE.findall("sem mencao aqui") == []


def test_accented_names():
    assert "Centavão" in MENTION_RE.findall("@Centavão precisa revisar")
