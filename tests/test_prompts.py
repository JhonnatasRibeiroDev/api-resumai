from app.llm.prompts import split_text_into_chunks, truncate_text


def test_truncate_text_when_shorter_than_limit() -> None:
    text, truncated = truncate_text("abc", 10)

    assert text == "abc"
    assert truncated is False


def test_truncate_text_when_longer_than_limit() -> None:
    text, truncated = truncate_text("abcdef", 3)

    assert text == "abc"
    assert truncated is True


def test_split_text_into_chunks_with_overlap() -> None:
    chunks, truncated = split_text_into_chunks("abcdefghijklmnopqrst", 8, 2, 3)

    assert chunks == ["abcdefgh", "ghijklmn", "mnopqrst"]
    assert truncated is False


def test_split_text_marks_truncated_when_max_chunks_is_reached() -> None:
    chunks, truncated = split_text_into_chunks("abcdefghijklmnopqrstuvwxyz", 8, 2, 2)

    assert chunks == ["abcdefgh", "ghijklmn"]
    assert truncated is True
