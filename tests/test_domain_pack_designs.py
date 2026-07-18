from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from law_firm_digital_twin.case_manifest import (
    build_capability_registry,
    build_population_blueprints,
)
from law_firm_digital_twin.domain_pack_design_contracts import (
    DesignOnlyLitigationDomainPack,
)
from law_firm_digital_twin.domain_pack_design_validator import (
    build_public_domain_pack_design_catalog,
    validate_design_only_domain_packs,
)
from law_firm_digital_twin.domain_pack_designs import (
    COMMON_PROHIBITED_PERSONA_USES,
    build_design_only_domain_packs,
    domain_pack_design_counts,
)
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.specialist_mesh_contracts import EvidenceDomainPack


def packs():
    return build_design_only_domain_packs(build_capability_registry())


def codes(items) -> set[str]:
    return {item.code for item in validate_design_only_domain_packs(items).findings}


def replace_pack(items, index, value):
    return (*items[:index], value, *items[index + 1 :])


def test_design_catalog_is_deterministic_complete_and_nonexecutable() -> None:
    first = packs()
    replay = packs()
    assert first == replay
    assert len(first) == 8
    assert domain_pack_design_counts(first) == {
        "artifact_families": 80,
        "expert_disciplines": 31,
        "lifecycle_stages": 80,
        "organization_contexts": 37,
        "packs": 8,
        "persona_roles": 62,
    }
    report = validate_design_only_domain_packs(first)
    assert report.passed
    assert all(isinstance(item, DesignOnlyLitigationDomainPack) for item in first)
    assert all(not isinstance(item, EvidenceDomainPack) for item in first)
    assert all(item.runtime_execution is False for item in first)
    assert all(item.external_source_access is False for item in first)
    assert all(item.canonical_truth_write is False for item in first)
    assert all(item.learning_state == "not_eligible" for item in first)


def test_every_design_family_matches_manifest_artifacts_experts_and_roles() -> None:
    registry = build_capability_registry()
    family_by_id = {item.family_id: item for item in registry.case_families}
    for pack in build_design_only_domain_packs(registry):
        family = family_by_id[pack.case_family_id]
        assert family.readiness == "design_only"
        assert {item.artifact_family_id for item in pack.artifact_families} == set(
            family.required_evidence_capabilities
        )
        assert {item.discipline_id for item in pack.expert_disciplines} == set(
            family.expert_domains
        )
        assert set(family.required_roles).issubset(
            item.role_id for item in pack.persona_roles
        )
        assert all(len(item.expected_metadata_keys) >= 4 for item in pack.artifact_families)
        assert all(item.custody_risk_ids for item in pack.artifact_families)
        assert all(item.version_risk_ids for item in pack.artifact_families)
        assert all(len(item.material_family_ids) >= 2 for item in pack.expert_disciplines)


def test_design_only_families_cannot_generate_population_blueprints() -> None:
    for pack in packs():
        with pytest.raises(ValueError, match="design-only"):
            build_population_blueprints(
                "domain-pack-design-cannot-activate",
                1,
                case_family_id=pack.case_family_id,
            )


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_code"),
    (
        ("status", "active_g2", "DPD-009"),
        ("runtime_execution", True, "DPD-009"),
        ("external_source_access", True, "DPD-009"),
        ("canonical_truth_write", True, "DPD-009"),
        ("source_admission_state", "admitted", "DPD-009"),
        ("learning_state", "eligible", "DPD-009"),
        ("activation_gate", "string_receipt_bypass", "DPD-009"),
        ("case_family_manifest_hash", "0" * 64, "DPD-007"),
        ("validator_ids", (), "DPD-057"),
    ),
)
def test_authority_and_activation_mutations_fail_closed(
    field_name: str,
    field_value: object,
    expected_code: str,
) -> None:
    items = packs()
    forged = replace(items[0], **{field_name: field_value})
    assert expected_code in codes(replace_pack(items, 0, forged))


def test_cross_reference_lifecycle_and_stereotype_mutations_fail_closed() -> None:
    items = packs()
    pack = items[0]
    artifact = replace(pack.artifact_families[0], author_role_ids=("unknown_role",))
    forged = replace(
        pack,
        artifact_families=(artifact, *pack.artifact_families[1:]),
    )
    assert "DPD-022" in codes(replace_pack(items, 0, forged))

    expert = replace(pack.expert_disciplines[0], material_family_ids=("unknown", "also_unknown"))
    forged = replace(
        pack,
        expert_disciplines=(expert, *pack.expert_disciplines[1:]),
    )
    assert "DPD-031" in codes(replace_pack(items, 0, forged))

    persona = replace(pack.persona_roles[0], prohibited_causal_uses=())
    forged = replace(pack, persona_roles=(persona, *pack.persona_roles[1:]))
    assert "DPD-038" in codes(replace_pack(items, 0, forged))

    stage = replace(pack.lifecycle_stages[0], predecessor_ids=("closeout",))
    forged = replace(pack, lifecycle_stages=(stage, *pack.lifecycle_stages[1:]))
    assert "DPD-020" in codes(replace_pack(items, 0, forged))


def test_private_and_live_source_classes_cannot_be_redeclared_as_safe() -> None:
    items = packs()
    pack = items[0]
    for forbidden_source in pack.forbidden_source_classes:
        artifact = replace(
            pack.artifact_families[0],
            allowed_synthetic_source_classes=(forbidden_source,),
        )
        forged = replace(
            pack,
            artifact_families=(artifact, *pack.artifact_families[1:]),
        )
        assert codes(replace_pack(items, 0, forged)) & {"DPD-029", "DPD-046"}
    forged = replace(pack, forbidden_source_classes=())
    assert "DPD-045" in codes(replace_pack(items, 0, forged))
    artifact = replace(pack.artifact_families[0], prohibited_content_classes=())
    forged = replace(
        pack,
        artifact_families=(artifact, *pack.artifact_families[1:]),
    )
    assert "DPD-030" in codes(replace_pack(items, 0, forged))


def test_expert_method_and_conclusion_disclaimers_cannot_hide_truth_claims() -> None:
    items = packs()
    pack = items[0]
    expert = pack.expert_disciplines[0]
    attacks = (
        (replace(expert, method_categories=("real_patient_diagnosis",)), "DPD-034"),
        (replace(expert, limitation_categories=("no_limits",)), "DPD-047"),
        (replace(expert, forbidden_conclusion_ids=("legal_conclusion",)), "DPD-048"),
        (replace(expert, independence_check_ids=("self_approval",)), "DPD-035"),
        (replace(expert, cross_domain_escalation_ids=("never_escalate",)), "DPD-058"),
        (replace(expert, qualification_fixture_id="fixture.unqualified"), "DPD-059"),
    )
    for attacked, expected_code in attacks:
        forged = replace(
            pack,
            expert_disciplines=(attacked, *pack.expert_disciplines[1:]),
        )
        assert expected_code in codes(replace_pack(items, 0, forged))


def test_persona_and_organization_disclaimers_cannot_hide_stereotype_causes() -> None:
    items = packs()
    pack = items[0]
    persona = pack.persona_roles[0]
    persona_attacks = (
        (replace(persona, memory_process_ids=("mbti_memory_style",)), "DPD-039"),
        (replace(persona, communication_context_ids=("class_determines_grammar",)), "DPD-049"),
        (replace(persona, pressure_factor_ids=("class_determines_grammar",)), "DPD-050"),
        (
            replace(
                persona,
                organization_interface_ids=(persona.organization_side, "left_right_brain"),
            ),
            "DPD-051",
        ),
        (replace(persona, authority_categories=("credibility_authority",)), "DPD-052"),
    )
    for attacked, expected_code in persona_attacks:
        forged = replace(pack, persona_roles=(attacked, *pack.persona_roles[1:]))
        assert expected_code in codes(replace_pack(items, 0, forged))

    organization = pack.organization_contexts[0]
    organization_attacks = (
        (replace(organization, systems_and_records=("real_client_files",)), "DPD-042"),
        (replace(organization, workflow_constraints=("mbti_workflow",)), "DPD-053"),
        (
            replace(organization, review_and_escalation_paths=("protected_trait_review",)),
            "DPD-054",
        ),
        (replace(organization, retention_and_versioning_patterns=("class_retention",)), "DPD-055"),
        (
            replace(
                organization,
                incentive_or_resource_pressures=("education_equals_intelligence",),
            ),
            "DPD-056",
        ),
    )
    for attacked, expected_code in organization_attacks:
        forged = replace(
            pack,
            organization_contexts=(attacked, *pack.organization_contexts[1:]),
        )
        assert expected_code in codes(replace_pack(items, 0, forged))


def test_personas_use_mechanisms_not_personality_or_demographic_proxies() -> None:
    for pack in packs():
        for persona in pack.persona_roles:
            assert set(COMMON_PROHIBITED_PERSONA_USES).issubset(
                persona.prohibited_causal_uses
            )
            assert {
                "observation_opportunity",
                "encoding_conditions",
                "elapsed_time",
                "intervening_information",
                "retrieval_confidence",
                "revision_or_correction_history",
            }.issubset(persona.memory_process_ids)
            assert "audience_and_purpose" in persona.communication_context_ids
            assert persona.time_varying is True


def test_expert_blueprints_are_source_bounded_and_cannot_claim_execution() -> None:
    for pack in packs():
        for expert in pack.expert_disciplines:
            assert expert.runtime_execution is False
            assert expert.legal_or_medical_truth_claims is False
            assert expert.credential_verification is False
            assert expert.permitted_output_boundary == "scope_method_limitations_only"
            assert "legal_conclusion" in expert.forbidden_conclusion_ids
            assert "writer_checker_independence" in expert.independence_check_ids
            assert expert.method_categories
            assert expert.limitation_categories


def test_public_catalog_is_aggregate_and_contains_no_source_like_payloads() -> None:
    catalog = build_public_domain_pack_design_catalog(packs())
    assert catalog["pack_count"] == 8
    assert catalog["active_family_count"] == 0
    assert catalog["runtime_execution_count"] == 0
    assert catalog["source_admitted_pack_count"] == 0
    assert catalog["learning_eligible_pack_count"] == 0
    assert catalog["persona_states_included"] is False
    assert catalog["source_rows_included"] is False
    assert catalog["artifact_bodies_included"] is False
    text = canonical_json(catalog).lower()
    for forbidden in (
        "artifact_families",
        "material_family_ids",
        "persona_roles",
        "knowledge_artifact",
        "fact_domain_ids",
        "author_role_ids",
        "recipient_role_ids",
        "credential",
        "http://",
        "https://",
        "openai",
        "anthropic",
        "composer",
    ):
        assert forbidden not in text


def test_checked_in_public_design_catalog_matches_builder() -> None:
    expected = build_public_domain_pack_design_catalog(packs())
    path = (
        Path(__file__).resolve().parents[1]
        / "generated"
        / "g2-domain-pack-designs-v1"
        / "catalog.json"
    )
    assert path.read_text(encoding="utf-8") == canonical_json(expected) + "\n"
