from app.analyzer import BasicAnalyzer
from app.diagnosis import HeuristicDiagnoser


def test_diagnosis_limits_and_cautious_content():
    analysis = BasicAnalyzer().analyze("Students write. Students write. Students write. Students write.")
    result = HeuristicDiagnoser().diagnose(analysis)
    assert len(result.strengths) <= 1
    assert len(result.improvement_priorities) <= 2
    assert [item.diagnosis_id for item in result.all_signals] == [
        f"D{index:03d}" for index in range(1, len(result.all_signals) + 1)
    ]
    assert all(item.rule_version == "prototype-diagnosis-v0.1.1" for item in result.all_signals)
    assert all(item.source_metrics for item in result.strengths + result.improvement_priorities)
    assert all(any(word in item.interpretation.lower() for word in ("may", "suggest", "worth")) for item in result.improvement_priorities)
    assert all("not a validated judgment" in item.limitation for item in result.strengths + result.improvement_priorities)
    assert not any("grammar ability is poor" in item.evidence.lower() for item in result.improvement_priorities)
