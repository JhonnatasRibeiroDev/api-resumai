from app.llm.prompts import truncate_text


def test_truncate_text_when_shorter_than_limit() -> None:
    text, truncated = truncate_text("abc", 10)

    assert text == "abc"
    assert truncated is False


def test_truncate_text_when_longer_than_limit() -> None:
    text, truncated = truncate_text("abcdef", 3)

    assert text == "abc"
    assert truncated is True
