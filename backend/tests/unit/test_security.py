from src.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("hamster123")
    assert h != "hamster123"
    assert verify_password("hamster123", h) is True
    assert verify_password("errado", h) is False


def test_access_token_roundtrip():
    token = create_access_token("user-123", {"extra": "x"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["extra"] == "x"


def test_refresh_token_hash_matches():
    raw, hashed = new_refresh_token()
    assert hashed == hash_token(raw)
    assert hashed != raw
