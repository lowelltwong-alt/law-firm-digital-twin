from __future__ import annotations

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    validate_case_compilation,
)
from law_firm_digital_twin.evidence_contracts import (
    detect_staged_conflicts,
    validate_staged_artifact,
)
from law_firm_digital_twin.persona_state import validate_persona_snapshot
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def test_projection_evidence_and_persona_cores_compose_without_admission() -> None:
    compilations = compile_population_fixture(
        seed="j130-contract-lock",
        count=10,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    assert len(compilations) == 10
    for compilation in compilations:
        assert validate_case_compilation(compilation).passed is True
        assert all(
            validate_persona_snapshot(state).passed
            for state in compilation.persona_states
        )
        assert all(
            validate_staged_artifact(staged, projection).passed
            for staged, projection in zip(
                compilation.staged_artifacts,
                compilation.renderer_projections,
                strict=True,
            )
        )
        assert all(
            receipt.canonical_admission is False
            for receipt in compilation.local_shape_receipts
        )


def test_integration_conflict_detection_uses_artifacts_not_design_purpose() -> None:
    compilations = compile_population_fixture(
        seed="j130-conflict-lock",
        count=10,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    detected_any = False
    for compilation in compilations:
        detected = detect_staged_conflicts(compilation.staged_artifacts)
        if detected:
            detected_any = True
        assert "test independent detection" not in repr(detected).lower()
    assert detected_any is True

