"""Prohibited-claim scans: every composed WU3 output must pass the strict
no-normative-claims scan, and the WU3 source files themselves must not carry
unsupported claims (documentation-mode exemption for prohibition text)."""

from __future__ import annotations

from pathlib import Path

from app.learner.normative import NormativeClaimsScanner


SCANNER = NormativeClaimsScanner()
WAVE3_ROOT = Path(__file__).resolve().parents[2] / "app" / "l2" / "wave3"


class TestComposedOutputScans:
    def test_adaptive_recommendation_payload_clean(self, adaptive) -> None:
        payload = adaptive["service"].recommend("L-ADAPT-01").model_dump(mode="json")
        assert SCANNER.scan_mapping(payload) == []

    def test_tutor_payloads_clean(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []
        decision = tutor_env["tutor"].decline(
            "L-TUTOR-01", recommendation.recommendation_id,
        )
        assert SCANNER.scan_mapping(decision.model_dump(mode="json")) == []

    def test_mini_writing_payload_clean(self, mini) -> None:
        result = mini["service"].submit(
            "L-MINI-01", mini["task"].task_id,
            "Cities should build more parks because green spaces improve health.",
        )
        assert SCANNER.scan_mapping(result.model_dump(mode="json")) == []


class TestSourceFileScans:
    def test_wave3_source_has_no_unsupported_claims(self) -> None:
        """Strict scan over the WU3 product source.

        Prohibition text (e.g. \"does not establish mastery\") is exempted
        line-by-line per the WU-D F1-resolution convention; any assertion
        line without a prohibition marker is flagged.
        """
        findings: list[str] = []
        for path in sorted(WAVE3_ROOT.rglob("*.py")):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1,
            ):
                for violation in SCANNER.scan_text(
                    line, documentation=True, location=f"{path.name}:{lineno}",
                ):
                    findings.append(
                        f"{path.name}:{lineno}: {violation.term}: {violation.snippet}"
                    )
        assert findings == []
