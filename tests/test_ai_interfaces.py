from src.ai_interfaces import AnalysisContext, AnalysisResult, validate_result


def test_context_converts_processed_metrics_to_evidence():
    context = AnalysisContext.from_mapping(2026, "Italy", "R", {"fastest_lap": 84.2})
    assert context.evidence[0].source == "fastest_lap"
    assert context.evidence[0].value == 84.2


def test_result_validation_rejects_unknown_evidence_sources():
    context = AnalysisContext.from_mapping(2026, "Italy", "R", {"fastest_lap": 84.2})
    result = AnalysisResult("Answer", evidence_sources=("weather",))
    assert validate_result(result, context) == ["weather"]

