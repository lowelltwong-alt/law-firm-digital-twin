from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .hashio import digest
from .world import PersonaProfile


PERSONA_CORE_REVISION = "persona-state-g2-v1"
SAFE_CAUSAL_POLICY = (
    "contextual_influence_only; no dimension determines intelligence, grammar, "
    "credibility, competence, protected status, liability, or outcome"
)
PROHIBITED_CAUSAL_SHORTCUTS = (
    "mbti_as_cause",
    "left_right_brain",
    "education_equals_intelligence",
    "class_determines_grammar",
    "profession_determines_voice",
    "protected_attribute_outcome_rule",
)


@dataclass(frozen=True)
class RelationshipState:
    relationship_id: str
    world_namespace: str
    matter_namespace: str
    source_actor_id: str
    target_actor_id: str
    as_of_day: int
    relationship_kind: str
    trust_band: str
    power_direction: str
    communication_norm: str
    shared_fact_ids: tuple[str, ...]
    revision: int = 1

    @property
    def state_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class PersonaStateSnapshot:
    state_id: str
    world_namespace: str
    matter_namespace: str
    actor_id: str
    role_id: str
    organization: str
    as_of_day: int
    revision: int
    synthetic_context: str
    training_context: str
    active_goals: tuple[str, ...]
    working_style: str
    workload_band: str
    stress_band: str
    attention_focus: str
    memory_mode: tuple[tuple[str, str], ...]
    voice_constraints: tuple[tuple[str, str], ...]
    channel_habits: tuple[str, ...]
    knowledge_fact_ids: tuple[str, ...]
    knowledge_assertion_ids: tuple[str, ...]
    authority_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    prior_state_hash: str | None
    core_revision: str = PERSONA_CORE_REVISION
    causal_policy: str = SAFE_CAUSAL_POLICY
    prohibited_shortcuts: tuple[str, ...] = PROHIBITED_CAUSAL_SHORTCUTS

    @property
    def state_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class RendererPersonaView:
    view_id: str
    world_namespace: str
    matter_namespace: str
    persona_state_id: str
    persona_state_hash: str
    actor_id: str
    role_id: str
    organization: str
    as_of_day: int
    synthetic_context: str
    training_context: str
    active_goals: tuple[str, ...]
    working_style: str
    workload_band: str
    stress_band: str
    attention_focus: str
    memory_mode: tuple[tuple[str, str], ...]
    voice_constraints: tuple[tuple[str, str], ...]
    channel_habits: tuple[str, ...]
    allowed_fact_ids: tuple[str, ...]
    allowed_assertion_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    causal_policy: str
    core_revision: str

    @property
    def view_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class PersonaValidationReport:
    passed: bool
    errors: tuple[str, ...]
    state_hash: str


def _bounded_band(token: int, bands: tuple[str, ...]) -> str:
    return bands[token % len(bands)]


def _channel_habits(profile: PersonaProfile) -> tuple[str, ...]:
    by_role = {
        "lawyer": ("email", "memo", "meeting_notes"),
        "paralegal": ("email", "task_list", "custody_log"),
        "witness": ("email", "meeting", "business_record"),
        "carrier": ("email", "claim_system_note"),
        "billing": ("billing_system", "email"),
        "docketing": ("docket_system", "email"),
        "deadline_reviewer": ("docket_system", "review_note"),
        "expert": ("report", "email"),
        "intake": ("intake_form", "email"),
        "conflicts": ("conflicts_system", "email"),
    }
    return by_role.get(profile.role_id, ("email", "business_record"))


def compile_persona_snapshot(
    profile: PersonaProfile,
    *,
    world_namespace: str,
    matter_namespace: str,
    as_of_day: int,
    knowledge_fact_ids: Iterable[str],
    knowledge_assertion_ids: Iterable[str] = (),
    authority_ids: Iterable[str] = (),
    relationship_ids: Iterable[str] = (),
    revision: int = 1,
    prior_state_hash: str | None = None,
) -> PersonaStateSnapshot:
    if not world_namespace:
        raise ValueError("world_namespace_required")
    if not matter_namespace:
        raise ValueError("matter_namespace_required")
    if as_of_day < 0:
        raise ValueError("as_of_day_invalid")
    if revision < 1:
        raise ValueError("persona_revision_invalid")
    knowledge = tuple(sorted(set(knowledge_fact_ids)))
    knowledge_assertions = tuple(sorted(set(knowledge_assertion_ids)))
    authority = tuple(sorted(set(authority_ids)))
    relationships = tuple(sorted(set(relationship_ids)))
    state_token = int(
        digest(
            {
                "world_namespace": world_namespace,
                "matter_namespace": matter_namespace,
                "actor_id": profile.actor_id,
                "as_of_day": as_of_day,
                "revision": revision,
            }
        )[:8],
        16,
    )
    workload = _bounded_band(state_token, ("low", "ordinary", "elevated", "high"))
    stress = _bounded_band(state_token // 7, ("settled", "alert", "pressured", "strained"))
    memory = (
        ("encoding", profile.memory.encoding),
        ("retrieval", profile.memory.retrieval),
        ("confidence_calibration", profile.memory.confidence_calibration),
        ("stress_effect", profile.memory.stress_effect),
    )
    voice = (
        ("register", profile.voice.register),
        ("sentence_style", profile.voice.sentence_style),
        ("directness", profile.voice.directness),
        ("organization", profile.voice.organization),
        ("revision_habit", profile.voice.revision_habit),
        ("signature", profile.voice.signature),
    )
    state_id = f"PSTATE-{digest({'world': world_namespace, 'matter': matter_namespace, 'actor': profile.actor_id, 'day': as_of_day, 'revision': revision})[:18]}"
    snapshot = PersonaStateSnapshot(
        state_id=state_id,
        world_namespace=world_namespace,
        matter_namespace=matter_namespace,
        actor_id=profile.actor_id,
        role_id=profile.role_id,
        organization=profile.organization,
        as_of_day=as_of_day,
        revision=revision,
        synthetic_context=profile.synthetic_background,
        training_context=profile.training,
        active_goals=profile.goals,
        working_style=profile.working_style,
        workload_band=workload,
        stress_band=stress,
        attention_focus=f"{profile.working_style}; current workload {workload}",
        memory_mode=memory,
        voice_constraints=voice,
        channel_habits=_channel_habits(profile),
        knowledge_fact_ids=knowledge,
        knowledge_assertion_ids=knowledge_assertions,
        authority_ids=authority,
        relationship_ids=relationships,
        prior_state_hash=prior_state_hash,
    )
    report = validate_persona_snapshot(snapshot)
    if not report.passed:
        raise ValueError(";".join(report.errors))
    return snapshot


def project_persona_for_renderer(
    snapshot: PersonaStateSnapshot,
    *,
    allowed_fact_ids: Iterable[str],
    allowed_assertion_ids: Iterable[str] = (),
) -> RendererPersonaView:
    requested = tuple(sorted(set(allowed_fact_ids)))
    unknown = sorted(set(requested) - set(snapshot.knowledge_fact_ids))
    if unknown:
        raise ValueError(f"knowledge_frontier_violation:{unknown}")
    requested_assertions = tuple(sorted(set(allowed_assertion_ids)))
    unknown_assertions = sorted(
        set(requested_assertions) - set(snapshot.knowledge_assertion_ids)
    )
    if unknown_assertions:
        raise ValueError(f"assertion_grant_violation:{unknown_assertions}")
    return RendererPersonaView(
        view_id=f"PVIEW-{digest({'state': snapshot.state_hash, 'facts': requested, 'assertions': requested_assertions})[:18]}",
        world_namespace=snapshot.world_namespace,
        matter_namespace=snapshot.matter_namespace,
        persona_state_id=snapshot.state_id,
        persona_state_hash=snapshot.state_hash,
        actor_id=snapshot.actor_id,
        role_id=snapshot.role_id,
        organization=snapshot.organization,
        as_of_day=snapshot.as_of_day,
        synthetic_context=snapshot.synthetic_context,
        training_context=snapshot.training_context,
        active_goals=snapshot.active_goals,
        working_style=snapshot.working_style,
        workload_band=snapshot.workload_band,
        stress_band=snapshot.stress_band,
        attention_focus=snapshot.attention_focus,
        memory_mode=snapshot.memory_mode,
        voice_constraints=snapshot.voice_constraints,
        channel_habits=snapshot.channel_habits,
        allowed_fact_ids=requested,
        allowed_assertion_ids=requested_assertions,
        relationship_ids=snapshot.relationship_ids,
        causal_policy=snapshot.causal_policy,
        core_revision=snapshot.core_revision,
    )


def validate_persona_snapshot(snapshot: PersonaStateSnapshot) -> PersonaValidationReport:
    errors: list[str] = []
    if not snapshot.world_namespace:
        errors.append("world_namespace_required")
    if not snapshot.matter_namespace:
        errors.append("matter_namespace_required")
    if snapshot.as_of_day < 0:
        errors.append("as_of_day_invalid")
    if snapshot.revision < 1:
        errors.append("persona_revision_invalid")
    if len(snapshot.knowledge_fact_ids) != len(set(snapshot.knowledge_fact_ids)):
        errors.append("duplicate_knowledge_fact")
    if len(snapshot.knowledge_assertion_ids) != len(set(snapshot.knowledge_assertion_ids)):
        errors.append("duplicate_knowledge_assertion")
    if len(snapshot.relationship_ids) != len(set(snapshot.relationship_ids)):
        errors.append("duplicate_relationship")
    if snapshot.causal_policy != SAFE_CAUSAL_POLICY:
        errors.append("unsafe_causal_policy")
    if set(snapshot.prohibited_shortcuts) != set(PROHIBITED_CAUSAL_SHORTCUTS):
        errors.append("prohibited_shortcut_boundary_incomplete")
    if not snapshot.voice_constraints or not snapshot.memory_mode:
        errors.append("persona_fidelity_fields_missing")
    if snapshot.core_revision != PERSONA_CORE_REVISION:
        errors.append("stale_core_revision")
    return PersonaValidationReport(not errors, tuple(errors), snapshot.state_hash)


def validate_relationship_state(
    relationship: RelationshipState,
    known_actor_ids: Iterable[str],
) -> tuple[str, ...]:
    errors: list[str] = []
    known = set(known_actor_ids)
    if relationship.source_actor_id not in known or relationship.target_actor_id not in known:
        errors.append("relationship_unknown_actor")
    if relationship.source_actor_id == relationship.target_actor_id:
        errors.append("relationship_self_edge")
    if not relationship.world_namespace:
        errors.append("relationship_world_missing")
    if not relationship.matter_namespace:
        errors.append("relationship_matter_missing")
    if relationship.as_of_day < 0 or relationship.revision < 1:
        errors.append("relationship_time_or_revision_invalid")
    return tuple(errors)

