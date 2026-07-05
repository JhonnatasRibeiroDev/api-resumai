from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password_hash = hash_password("minha-senha-segura")

    assert password_hash != "minha-senha-segura"
    assert verify_password("minha-senha-segura", password_hash)
    assert not verify_password("senha-errada", password_hash)


def test_access_token_roundtrip() -> None:
    settings = Settings(jwt_secret="token-secret")
    token = create_access_token("user-id", settings)

    assert decode_access_token(token, settings) == "user-id"
    assert decode_access_token(token, Settings(jwt_secret="other-secret")) is None
