from __future__ import annotations

from dataclasses import replace

import pytest

from law_firm_digital_twin.persona_state import (
    PROHIBITED_CAUSAL_SHORTCUTS,
    RelationshipState,
    compile_persona_snapshot,
    project_persona_for_renderer,
    validate_persona_snapshot,
    validate_relationship_state,
)
from law_firm_digital_twin.world import build_personas


def test_persona_snapshot_is_deterministic_contextual_and_revision_bound() -> None:
    profile = build_personas()["responsible_lawyer"]
    first = compile_persona_snapshot(
        profile,
        world_namespace="WNS-persona-test",
        matter_namespace="MNS-persona-test",
        as_of_day=50,
        knowledge_fact_ids=("referral_summary", "policy_process"),
        authority_ids=("legal_work",),
        relationship_ids=("REL-client",),
    )
    replay = compile_persona_snapshot(
        profile,
        world_namespace="WNS-persona-test",
        matter_namespace="MNS-persona-test",
        as_of_day=50,
        knowledge_fact_ids=("policy_process", "referral_summary"),
        authority_ids=("legal_work",),
        relationship_ids=("REL-client",),
    )
    later = compile_persona_snapshot(
        profile,
        world_namespace="WNS-persona-test",
        matter_namespace="MNS-persona-test",
        as_of_day=80,
        knowledge_fact_ids=("referral_summary", "policy_process", "decision_status"),
        authority_ids=("legal_work",),
        relationship_ids=("REL-client",),
        revision=2,
        prior_state_hash=first.state_hash,
    )
    assert first == replay
    assert first.state_hash == replay.state_hash
    assert later.state_hash != first.state_hash
    assert later.prior_state_hash == first.state_hash
    assert validate_persona_snapshot(first).passed is True


def test_renderer_persona_view_is_least_privilege() -> None:
    profile = build_personas()["hr_witness"]
    state = compile_persona_snapshot(
        profile,
        world_namespace="WNS-persona-view",
        matter_namespace="MNS-persona-view",
        as_of_day=40,
        knowledge_fact_ids=("policy_process", "decision_status"),
    )
    view = project_persona_for_renderer(
        state,
        allowed_fact_ids=("decision_status",),
    )
    assert view.allowed_fact_ids == ("decision_status",)
    assert "policy_process" not in view.allowed_fact_ids
    assert view.persona_state_hash == state.state_hash
    with pytest.raises(ValueError, match="knowledge_frontier_violation"):
        project_persona_for_renderer(
            state,
            allowed_fact_ids=("future_outcome",),
        )


def test_persona_contract_rejects_causal_shortcut_tampering() -> None:
    state = compile_persona_snapshot(
        build_personas()["manager_witness"],
        world_namespace="WNS-causal",
        matter_namespace="MNS-causal",
        as_of_day=38,
        knowledge_fact_ids=("decision_status",),
    )
    unsafe = replace(
        state,
        causal_policy="mbti determines writing and credibility",
        prohibited_shortcuts=("mbti_as_cause",),
    )
    report = validate_persona_snapshot(unsafe)
    assert report.passed is False
    assert set(PROHIBITED_CAUSAL_SHORTCUTS).issubset(state.prohibited_shortcuts)
    assert "unsafe_causal_policy" in report.errors
    assert "prohibited_shortcut_boundary_incomplete" in report.errors


def test_persona_state_rejects_invalid_time_revision_and_world() -> None:
    profile = build_personas()["hr_witness"]
    with pytest.raises(ValueError, match="world_namespace_required"):
        compile_persona_snapshot(
            profile,
            world_namespace="",
            matter_namespace="MNS-valid",
            as_of_day=1,
            knowledge_fact_ids=(),
        )
    with pytest.raises(ValueError, match="as_of_day_invalid"):
        compile_persona_snapshot(
            profile,
            world_namespace="WNS-valid",
            matter_namespace="MNS-valid",
            as_of_day=-1,
            knowledge_fact_ids=(),
        )
    with pytest.raises(ValueError, match="persona_revision_invalid"):
        compile_persona_snapshot(
            profile,
            world_namespace="WNS-valid",
            matter_namespace="MNS-valid",
            as_of_day=1,
            knowledge_fact_ids=(),
            revision=0,
        )


def test_relationship_validation_is_directed_and_case_local() -> None:
    relationship = RelationshipState(
        relationship_id="REL-1",
        world_namespace="WNS-rel",
        matter_namespace="MNS-rel",
        source_actor_id="manager_witness",
        target_actor_id="hr_witness",
        as_of_day=38,
        relationship_kind="coworker",
        trust_band="uneven",
        power_direction="manager_operational_hr_advisory",
        communication_norm="brief_email_then_meeting",
        shared_fact_ids=("policy_process",),
    )
    assert validate_relationship_state(
        relationship,
        ("manager_witness", "hr_witness"),
    ) == ()
    forged = replace(relationship, target_actor_id="foreign_actor")
    assert "relationship_unknown_actor" in validate_relationship_state(
        forged,
        ("manager_witness", "hr_witness"),
    )


def test_persona_views_preserve_richness_without_personality_typing() -> None:
    profiles = build_personas()
    views = []
    for actor_id in ("responsible_lawyer", "litigation_paralegal", "hr_witness"):
        state = compile_persona_snapshot(
            profiles[actor_id],
            world_namespace="WNS-richness",
            matter_namespace="MNS-richness",
            as_of_day=50,
            knowledge_fact_ids=("shared_fact",),
        )
        views.append(
            project_persona_for_renderer(
                state,
                allowed_fact_ids=("shared_fact",),
            )
        )
    assert len({item.working_style for item in views}) == 3
    assert len({dict(item.voice_constraints)["signature"] for item in views}) == 3
    serialized = repr(views).lower()
    assert "mbti" not in serialized
    assert "left-brain" not in serialized
    assert all("contextual_influence_only" in item.causal_policy for item in views)

