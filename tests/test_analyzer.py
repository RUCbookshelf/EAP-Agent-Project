from app.analyzer import BasicAnalyzer


def test_basic_metrics_are_calculated():
    text = "However, students learn by writing. Students revise writing.\n\nTherefore, writing improves through practice."
    result = BasicAnalyzer().analyze(text)
    assert result.metrics["word_count"] == 13
    assert result.metrics["sentence_count"] == 3
    assert result.metrics["paragraph_count"] == 2
    assert result.metrics["average_sentence_length"] == 4.33
    assert result.metrics["unique_word_count"] == 10
    assert result.metrics["type_token_ratio"] == 0.769
    assert result.metrics["connective_count"] == 2
    assert result.metrics["repeated_content_words"] == {"writing": 3}
    assert "not a complete CALF" in result.limitations

