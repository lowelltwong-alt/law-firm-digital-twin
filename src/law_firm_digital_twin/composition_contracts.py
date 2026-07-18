from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .case_manifest import CapabilityRegistry, build_capability_registry
from .evidence_contracts import RendererArtifactProjection
from .communication_culture import (
    PRESENTATION_OPERATION_IDS,
    derive_individual_style,
    derive_organization_culture,
)

from .hashio import digest
from .persona_state import PROHIBITED_CAUSAL_SHORTCUTS


COMPOSITION_CORE_REVISION = "composition-contracts-g2-v1"
COMPOSITION_LEXICON_REVISION = "composition-lexicon-g2-v1"
G2_FIDELITY_STATEMENT = (
    "Synthetic G2 text composition fixture; not a native file, court-compliant "
    "filing, production business record, or real-world prediction."
)

SegmentFunction = Literal["assertion", "nonassertive", "metadata_label"]


@dataclass(frozen=True)
class ChannelCompositionContract:
    contract_id: str
    revision: str
    capability_id: str
    capability_revision: str
    family_id: str
    channel_kind: str
    rendered_media_type: Literal["text/plain"]
    allowed_target_native_formats: tuple[str, ...]
    required_sections: tuple[str, ...]
    assertion_section: str
    required_field_names: tuple[str, ...]
    permitted_style_operations: tuple[str, ...]
    permitted_nonassertive_block_ids: tuple[str, ...]
    prohibited_moves: tuple[str, ...]
    factuality_policy: str
    g2_fidelity_statement: str = G2_FIDELITY_STATEMENT

    @property
    def contract_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class WritingDispositionProjection:
    disposition_id: str
    world_namespace: str
    matter_namespace: str
    author_id: str
    recipient_ids: tuple[str, ...]
    channel_kind: str
    as_of_day: int
    source_persona_state_hash: str
    voice_signature: str
    organization_culture_hash: str
    individual_style_hash: str
    effective_geometry_signature: str
    culture_operation_ids: tuple[str, ...]
    writer_operation_ids: tuple[str, ...]
    style_controls: tuple[tuple[str, str], ...]
    memory_controls: tuple[tuple[str, str], ...]
    audience_mode: str
    channel_compatibility: Literal["native", "organizational_fallback"]
    allowed_style_operations: tuple[str, ...]
    prohibited_inferences: tuple[str, ...]
    core_revision: str = COMPOSITION_CORE_REVISION

    @property
    def disposition_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CompositionPlan:
    plan_id: str
    renderer_projection_hash: str
    channel_contract_hash: str
    writing_disposition_hash: str
    assertion_order: tuple[str, ...]
    section_plan: tuple[tuple[str, tuple[str, ...]], ...]
    style_operations: tuple[str, ...]
    nonassertive_block_ids: tuple[str, ...]
    variant_id: str
    deterministic_stream_key: str
    lexicon_revision: str
    prohibited_inferences: tuple[str, ...]
    core_revision: str = COMPOSITION_CORE_REVISION

    @property
    def plan_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class TextSegmentTrace:
    segment_id: str
    section_id: str
    rendered_text: str
    function: SegmentFunction
    assertion_ids: tuple[str, ...]
    style_operation_ids: tuple[str, ...]

    @property
    def segment_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class TextCompositionCandidate:
    candidate_id: str
    renderer_projection_hash: str
    composition_plan_hash: str
    contract_hash: str
    disposition_hash: str
    rendered_media_type: Literal["text/plain"]
    simulated_target_native_format: str
    body: str
    segments: tuple[TextSegmentTrace, ...]
    adapter_revision: str
    provider_class: Literal["deterministic_fixture"]
    synthetic_only: Literal[True]
    noncanonical: Literal[True]

    @property
    def candidate_hash(self) -> str:
        return digest(self)


_CHANNEL_SPECS = {
    "email": {
        "sections": ("header", "subject", "message", "closing", "disclosure"),
        "assertion_section": "message",
        "operations": (
            "lead_with_bottom_line",
            "context_before_update",
            "compact_geometry",
            "source_bounded_calibration",
            "audience_aware_opening",
        ),
    },
    "hris_record": {
        "sections": ("record_header", "fields", "note", "disclosure"),
        "assertion_section": "fields",
        "operations": (
            "field_led_record",
            "compact_geometry",
            "source_bounded_calibration",
        ),
    },
    "policy_document": {
        "sections": ("document_header", "scope", "directive", "process", "disclosure"),
        "assertion_section": "directive",
        "operations": (
            "numbered_policy_geometry",
            "chronological_order",
            "visible_revision_signal",
        ),
    },
    "structured_table": {
        "sections": ("table_header", "rows", "disclosure"),
        "assertion_section": "rows",
        "operations": (
            "plain_text_table_geometry",
            "compact_geometry",
            "amount_or_record_first",
        ),
    },
    "calendar": {
        "sections": ("event_header", "participants", "status", "notes", "disclosure"),
        "assertion_section": "status",
        "operations": (
            "calendar_field_geometry",
            "compact_geometry",
            "chronological_order",
        ),
    },
    "litigation_record": {
        "sections": (
            "intake_header",
            "reported_issue",
            "known_materials",
            "next_action",
            "disclosure",
        ),
        "assertion_section": "reported_issue",
        "operations": (
            "chronological_order",
            "source_bounded_calibration",
            "audience_aware_opening",
        ),
    },
    "expert_record": {
        "sections": (
            "report_header",
            "materials",
            "method",
            "observations",
            "limitations",
            "bounded_opinion",
            "disclosure",
        ),
        "assertion_section": "observations",
        "operations": (
            "materials_method_observation",
            "source_bounded_calibration",
            "visible_revision_signal",
        ),
    },
    "irrelevant_record": {
        "sections": (
            "notice_header",
            "ordinary_course_message",
            "nonresponsive_basis",
            "disclosure",
        ),
        "assertion_section": "ordinary_course_message",
        "operations": (
            "ordinary_course_geometry",
            "compact_geometry",
        ),
    },
}

_COMMON_PROHIBITED_MOVES = (
    "invent_fact",
    "omit_required_assertion",
    "mutate_assertion",
    "reconcile_conflict",
    "infer_credibility",
    "infer_intelligence",
    "infer_competence",
    "infer_liability",
    "infer_outcome",
    "claim_native_fidelity",
    "use_sealed_or_evaluator_context",
)

_CHANNEL_ALIASES = {
    "email": frozenset({"email"}),
    "hris_record": frozenset({"business_record"}),
    "policy_document": frozenset({"business_record"}),
    "structured_table": frozenset({"billing_system", "business_record"}),
    "calendar": frozenset({"calendar", "meeting"}),
    "litigation_record": frozenset({"intake_form", "business_record"}),
    "expert_record": frozenset({"report"}),
    "irrelevant_record": frozenset({"business_record", "email"}),
}


def build_channel_composition_contracts(
    registry: CapabilityRegistry | None = None,
) -> dict[str, ChannelCompositionContract]:
    registry = registry or build_capability_registry()
    contracts: dict[str, ChannelCompositionContract] = {}
    for capability in registry.evidence_capabilities:
        if capability.readiness != "active_g2":
            continue
        spec = _CHANNEL_SPECS.get(capability.channel_kind)
        if spec is None:
            raise ValueError(f"unsupported_channel_kind:{capability.channel_kind}")
        nonassertive = (
            tuple(
                f"{capability.channel_kind}.{kind}.{voice_family}.{index}"
                for kind in ("opening", "closing")
                for voice_family in ("direct", "contextual", "formal", "ledger", "service")
                for index in range(6)
            )
            + tuple(f"{capability.channel_kind}.section.{section}" for section in spec["sections"])
            + (f"{capability.channel_kind}.disclosure",)
        )
        contract = ChannelCompositionContract(
            contract_id=f"CHANNEL-{digest({'capability': capability.capability_id, 'revision': capability.revision, 'core': COMPOSITION_CORE_REVISION})[:18]}",
            revision=COMPOSITION_CORE_REVISION,
            capability_id=capability.capability_id,
            capability_revision=capability.revision,
            family_id=capability.family_id,
            channel_kind=capability.channel_kind,
            rendered_media_type="text/plain",
            allowed_target_native_formats=capability.allowed_native_formats,
            required_sections=spec["sections"],
            assertion_section=spec["assertion_section"],
            required_field_names=capability.required_fields,
            permitted_style_operations=tuple(
                sorted(
                    set(spec["operations"]) | set(PRESENTATION_OPERATION_IDS)
                )
            ),
            permitted_nonassertive_block_ids=nonassertive,
            prohibited_moves=_COMMON_PROHIBITED_MOVES,
            factuality_policy=(
                "assertion segments must be deterministic renderings of exact "
                "allowlisted assertions; all other prose must come from the "
                "versioned nonassertive lexicon"
            ),
        )
        contracts[capability.capability_id] = contract
    return contracts


def derive_writing_disposition(
    projection: RendererArtifactProjection,
    presentation_scope_commitment: str | None = None,
) -> WritingDispositionProjection:
    view = projection.persona_view
    culture = derive_organization_culture(
        projection, presentation_scope_commitment
    )
    individual_style = derive_individual_style(
        projection, culture, presentation_scope_commitment
    )
    voice = dict(view.voice_constraints)
    memory = dict(view.memory_mode)
    base_voice_signature = voice.get("signature", "")
    if not base_voice_signature:
        raise ValueError("voice_signature_missing")
    voice_signature = individual_style.effective_voice_signature
    audience_mode = (
        "record_only"
        if not projection.recipient_ids
        else "single_recipient"
        if len(projection.recipient_ids) == 1
        else "multi_recipient"
    )
    aliases = _CHANNEL_ALIASES.get(projection.channel_kind, frozenset())
    compatibility: Literal["native", "organizational_fallback"] = (
        "native"
        if aliases.intersection(view.channel_habits)
        else "organizational_fallback"
    )
    brevity = (
        "compressed"
        if view.workload_band == "high" or view.stress_band == "strained"
        else "ordinary"
    )
    style_controls = (
        ("register", voice.get("register", "bounded")),
        ("sentence_style", voice.get("sentence_style", "complete sentences")),
        ("directness", voice.get("directness", "moderate")),
        ("organization", voice.get("organization", "chronological")),
        ("revision_habit", voice.get("revision_habit", "review before issue")),
        ("brevity", brevity),
        ("opening_family", individual_style.opening_family_id),
        ("sentence_geometry", individual_style.sentence_geometry_id),
        ("organization_geometry", individual_style.organization_geometry_id),
        ("connective", individual_style.connective_id),
        ("closing", individual_style.closing_id),
        ("calibration", individual_style.calibration_id),
        ("attention", individual_style.attention_id),
        ("correction", individual_style.correction_id),
    )
    memory_controls = (
        ("encoding", memory.get("encoding", "source-bounded")),
        ("retrieval", memory.get("retrieval", "source-cued")),
        (
            "confidence_calibration",
            memory.get("confidence_calibration", "calibrated"),
        ),
        ("stress_effect", memory.get("stress_effect", "no factual effect")),
    )
    permitted = (
        set(_CHANNEL_SPECS[projection.channel_kind]["operations"])
        | set(PRESENTATION_OPERATION_IDS)
    )
    selected: list[str] = []
    organization = voice.get("organization", "")
    sentence_style = voice.get("sentence_style", "")
    directness = voice.get("directness", "")
    revision_habit = voice.get("revision_habit", "")
    if "bottom line" in organization or directness in {"high", "very high"}:
        selected.append("lead_with_bottom_line")
    if "chronological" in organization or "date" in organization:
        selected.append("chronological_order")
    if any(token in sentence_style for token in ("short", "fragment", "bullet", "line")):
        selected.append("compact_geometry")
    if any(token in revision_habit for token in ("version", "correction", "add", "history")):
        selected.append("visible_revision_signal")
    if projection.channel_kind == "expert_record":
        selected.append("materials_method_observation")
    if projection.channel_kind == "structured_table":
        selected.append("plain_text_table_geometry")
    if projection.channel_kind == "calendar":
        selected.append("calendar_field_geometry")
    selected.append("source_bounded_calibration")
    selected.extend(individual_style.selected_operation_ids)
    allowed = tuple(sorted(set(selected).intersection(permitted)))
    payload = {
        "world_namespace": projection.world_namespace,
        "matter_namespace": projection.matter_namespace,
        "author_id": projection.author_id,
        "recipient_ids": projection.recipient_ids,
        "channel_kind": projection.channel_kind,
        "as_of_day": projection.created_day,
        "source_persona_state_hash": view.persona_state_hash,
        "voice_signature": voice_signature,
        "organization_culture_hash": culture.culture_hash,
        "individual_style_hash": individual_style.style_hash,
        "effective_geometry_signature": individual_style.effective_geometry_signature,
        "culture_operation_ids": culture.permitted_operation_ids,
        "writer_operation_ids": individual_style.selected_operation_ids,
        "style_controls": style_controls,
        "memory_controls": memory_controls,
        "audience_mode": audience_mode,
        "channel_compatibility": compatibility,
        "allowed_style_operations": allowed,
        "prohibited_inferences": tuple(
            sorted(
                set(PROHIBITED_CAUSAL_SHORTCUTS)
                | set(individual_style.prohibited_inferences)
            )
        ),
        "core_revision": COMPOSITION_CORE_REVISION,
    }
    return WritingDispositionProjection(
        disposition_id=f"WDISP-{digest(payload)[:18]}",
        **payload,
    )

