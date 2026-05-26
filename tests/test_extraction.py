from seekflow.extraction.extractor import truncate_for_context


def test_truncate_for_context_limits_word_count() -> None:
    text = "word " * 4000
    result = truncate_for_context(text, max_words=1500)
    assert len(result.split()) <= 1500
