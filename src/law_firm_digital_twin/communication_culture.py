from __future__ import annotations

from dataclasses import dataclass

from .evidence_contracts import RendererArtifactProjection
from .hashio import digest
from .persona_state import PROHIBITED_CAUSAL_SHORTCUTS


COMMUNICATION_CULTURE_CORE_REVISION = "communication-culture-g2-v1"
COMMUNICATION_CATALOG_REVISION = "communication-presentation-catalog-g2-v1"
COMMUNICATION_CAUSAL_POLICY = (
    "presentation_only; operational conventions and explicit writer controls "
    "never determine facts, intelligence, grammar quality, credibility, "
    "competence, protected status, diligence, liability, or outcome"
)
PERSISTENT_ORGANIZATION_IDS = frozenset({"defense_firm"})

_RECORDKEEPING = (
    "field_first",
    "context_then_fields",
    "record_then_context",
)
_COORDINATION = (
    "direct_handoff",
    "threaded_update",
    "review_followup",
)
_REVIEW = (
    "single_pass_visible",
    "second_pair_of_eyes",
    "exception_escalation",
)
_CORRECTION = (
    "correction_visible",
    "correction_inline",
    "correction_reissue",
)
_CHANNEL_LAYOUTS = {
    "email": ("layout_fields_first", "layout_context_first", "layout_record_first"),
    "hris_record": ("layout_fields_first", "layout_record_first", "layout_context_first"),
    "policy_document": ("layout_context_first", "layout_fields_first", "layout_record_first"),
    "structured_table": ("layout_record_first", "layout_fields_first", "layout_context_first"),
    "calendar": ("layout_fields_first", "layout_context_first", "layout_record_first"),
    "litigation_record": ("layout_context_first", "layout_record_first", "layout_fields_first"),
    "expert_record": ("layout_record_first", "layout_context_first", "layout_fields_first"),
    "irrelevant_record": ("layout_context_first", "layout_fields_first", "layout_record_first"),
}
_OPENINGS = (
    "opening_direct",
    "opening_contextual",
    "opening_formal",
    "opening_ledger",
    "opening_service",
)
_SENTENCE_GEOMETRIES = (
    "geometry_compact_lines",
    "geometry_short_paragraph",
    "geometry_labeled_blocks",
)
_CONNECTIVES = (
    "connective_minimal",
    "connective_sequence",
    "connective_explicit",
)
_CLOSINGS = (
    "closing_action",
    "closing_confirmation",
    "closing_bounded",
)
_CALIBRATION = (
    "calibration_inline",
    "calibration_separate",
    "calibration_compact",
)
_ATTENTION = (
    "attention_event_first",
    "attention_record_first",
    "attention_action_first",
)
_PROHIBITED = tuple(
    sorted(
        set(PROHIBITED_CAUSAL_SHORTCUTS)
        | {
            "culture_determines_credibility",
            "culture_determines_competence",
            "culture_determines_diligence",
            "culture_determines_liability",
            "culture_determines_outcome",
            "demographic_dialect_generation",
            "raw_background_as_style",
            "training_as_intelligence",
            "role_as_voice",
            "merits_as_style",
            "evaluator_as_style",
        }
    )
)


PRESENTATION_OPERATION_IDS = tuple(
    sorted(
        set(_OPENINGS)
        | set(_SENTENCE_GEOMETRIES)
        | set(_CONNECTIVES)
        | set(_CLOSINGS)
        | set(_CALIBRATION)
        | set(_ATTENTION)
        | set(_CORRECTION)
        | {
            layout
            for layouts in _CHANNEL_LAYOUTS.values()
            for layout in layouts
        }
    )
)


@dataclass(frozen=True)
class OrganizationCultureProjection:
    culture_id: str
    organization_identity_commitment: str
    organization_id: str
    recordkeeping_protocol_id: str
    coordination_protocol_id: str
    review_protocol_id: str
    correction_protocol_id: str
    channel_conventions: tuple[tuple[str, str], ...]
    permitted_operation_ids: tuple[str, ...]
    source_scope_commitment: str
    causal_policy: str = COMMUNICATION_CAUSAL_POLICY
    prohibited_inferences: tuple[str, ...] = _PROHIBITED
    catalog_revision: str = COMMUNICATION_CATALOG_REVISION
    core_revision: str = COMMUNICATION_CULTURE_CORE_REVISION

    @property
    def culture_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class IndividualStyleProjection:
    style_id: str
    presentation_scope_commitment: str
    actor_id: str
    organization_id: str
    source_persona_state_hash: str
    culture_hash: str
    writer_pattern_id: str
    opening_family_id: str
    sentence_geometry_id: str
    organization_geometry_id: str
    connective_id: str
    closing_id: str
    calibration_id: str
    attention_id: str
    correction_id: str
    selected_operation_ids: tuple[str, ...]
    effective_voice_signature: str
    effective_geometry_signature: str
    causal_provenance: tuple[tuple[str, str], ...]
    prohibited_inferences: tuple[str, ...] = _PROHIBITED
    catalog_revision: str = COMMUNICATION_CATALOG_REVISION
    core_revision: str = COMMUNICATION_CULTURE_CORE_REVISION

    @property
    def style_hash(self) -> str:
        return digest(self)


def _select(options: tuple[str, ...], token: str, offset: int) -> str:
    index = int(token[offset : offset + 8], 16) % len(options)
    return options[index]


def _unqualified_presentation_scope(
    projection: RendererArtifactProjection,
) -> str:
    return digest(
        {
            "actor": projection.author_id,
            "organization": projection.persona_view.organization,
            "catalog": COMMUNICATION_CATALOG_REVISION,
            "boundary": "unqualified-test-only",
        }
    )


def derive_organization_identity_commitment(
    projection: RendererArtifactProjection,
    presentation_scope_commitment: str,
) -> str:
    payload = {
        "organization": projection.persona_view.organization,
        "catalog": COMMUNICATION_CATALOG_REVISION,
    }
    if projection.persona_view.organization not in PERSISTENT_ORGANIZATION_IDS:
        payload["presentation_scope"] = presentation_scope_commitment
    return digest(payload)


def derive_actor_identity_commitment(
    projection: RendererArtifactProjection,
    presentation_scope_commitment: str,
) -> str:
    organization_identity = derive_organization_identity_commitment(
        projection,
        presentation_scope_commitment,
    )
    return digest(
        {
            "organization_identity": organization_identity,
            "actor": projection.author_id,
            "catalog": COMMUNICATION_CATALOG_REVISION,
        }
    )



def derive_organization_culture(
    projection: RendererArtifactProjection,
    presentation_scope_commitment: str | None = None,
) -> OrganizationCultureProjection:
    if not isinstance(projection, RendererArtifactProjection):
        raise ValueError("renderer_projection_type_invalid")
    if not projection.synthetic_only:
        raise ValueError("synthetic_boundary_missing")
    organization_id = projection.persona_view.organization
    if not organization_id:
        raise ValueError("organization_id_missing")
    if presentation_scope_commitment is None:
        presentation_scope_commitment = _unqualified_presentation_scope(projection)
    if len(presentation_scope_commitment) != 64:
        raise ValueError("presentation_scope_commitment_invalid")
    organization_identity = derive_organization_identity_commitment(
        projection, presentation_scope_commitment
    )
    scope = {
        "organization_identity": organization_identity,
        "organization": organization_id,
        "catalog": COMMUNICATION_CATALOG_REVISION,
    }
    token = digest(scope)
    recordkeeping = _select(_RECORDKEEPING, token, 0)
    coordination = _select(_COORDINATION, token, 8)
    review = _select(_REVIEW, token, 16)
    correction = _select(_CORRECTION, token, 24)
    conventions = tuple(
        (
            channel,
            _select(layout_options, digest({"scope": scope, "channel": channel}), 0),
        )
        for channel, layout_options in sorted(_CHANNEL_LAYOUTS.items())
    )
    permitted = tuple(
        sorted(
            {
                value for _, value in conventions
            }
            | {
                correction,
                "opening_direct",
                "opening_contextual",
                "opening_formal",
                "opening_ledger",
                "opening_service",
                "geometry_compact_lines",
                "geometry_short_paragraph",
                "geometry_labeled_blocks",
                "connective_minimal",
                "connective_sequence",
                "connective_explicit",
                "closing_action",
                "closing_confirmation",
                "closing_bounded",
                "calibration_inline",
                "calibration_separate",
                "calibration_compact",
                "attention_event_first",
                "attention_record_first",
                "attention_action_first",
            }
        )
    )
    payload = {
        "organization_identity_commitment": organization_identity,
        "organization_id": organization_id,
        "recordkeeping_protocol_id": recordkeeping,
        "coordination_protocol_id": coordination,
        "review_protocol_id": review,
        "correction_protocol_id": correction,
        "channel_conventions": conventions,
        "permitted_operation_ids": permitted,
        "source_scope_commitment": digest(scope),
        "causal_policy": COMMUNICATION_CAUSAL_POLICY,
        "prohibited_inferences": _PROHIBITED,
        "catalog_revision": COMMUNICATION_CATALOG_REVISION,
        "core_revision": COMMUNICATION_CULTURE_CORE_REVISION,
    }
    return OrganizationCultureProjection(
        culture_id=f"CULTURE-{digest(payload)[:18]}",
        **payload,
    )


def derive_individual_style(
    projection: RendererArtifactProjection,
    culture: OrganizationCultureProjection,
    presentation_scope_commitment: str | None = None,
) -> IndividualStyleProjection:
    if not isinstance(projection, RendererArtifactProjection):
        raise ValueError("renderer_projection_type_invalid")
    if not isinstance(culture, OrganizationCultureProjection):
        raise ValueError("culture_projection_type_invalid")
    if presentation_scope_commitment is None:
        presentation_scope_commitment = _unqualified_presentation_scope(projection)
    if culture.organization_id != projection.persona_view.organization:
        raise ValueError("culture_organization_mismatch")
    expected_culture = derive_organization_culture(
        projection, presentation_scope_commitment
    )
    if culture != expected_culture:
        raise ValueError("noncanonical_culture_projection")
    voice_controls = tuple(
        (key, value)
        for key, value in projection.persona_view.voice_constraints
        if key
        in {
            "register",
            "sentence_style",
            "directness",
            "organization",
            "revision_habit",
            "signature",
        }
    )
    actor_identity = derive_actor_identity_commitment(
        projection, presentation_scope_commitment
    )
    stable_scope = {
        "actor_identity": actor_identity,
        "actor": projection.author_id,
        "organization": culture.organization_id,
        "culture": culture.culture_hash,
        "voice_controls": voice_controls,
        "catalog": COMMUNICATION_CATALOG_REVISION,
    }
    token = digest(stable_scope)
    geometry_token = digest(
        {
            "actor_identity": actor_identity,
            "presentation_episode": presentation_scope_commitment,
            "channel": projection.channel_kind,
            "catalog": COMMUNICATION_CATALOG_REVISION,
        }
    )
    layout_options = dict(culture.channel_conventions)
    layout = layout_options[projection.channel_kind]
    opening = _select(_OPENINGS, token, 0)
    sentence_geometry = _select(_SENTENCE_GEOMETRIES, geometry_token, 0)
    connective = _select(_CONNECTIVES, token, 16)
    closing = _select(_CLOSINGS, token, 24)
    calibration = _select(_CALIBRATION, digest({"stable": stable_scope, "kind": "calibration"}), 0)
    attention = _select(_ATTENTION, digest({"stable": stable_scope, "kind": "attention"}), 0)
    selected = (
        opening,
        sentence_geometry,
        layout,
    )
    if not set(selected).issubset(set(culture.permitted_operation_ids)):
        raise ValueError("style_operation_not_permitted_by_culture")
    writer_pattern_id = f"WRITER-{digest(stable_scope)[:18]}"
    effective_voice_signature = digest(
        {
            "opening": opening,
        }
    )[:16]
    effective_geometry_signature = digest(
        {
            "channel": projection.channel_kind,
            "sentence_geometry": sentence_geometry,
            "layout": layout,
        }
    )[:16]
    payload = {
        "presentation_scope_commitment": presentation_scope_commitment,
        "actor_id": projection.author_id,
        "organization_id": culture.organization_id,
        "source_persona_state_hash": projection.persona_view.persona_state_hash,
        "culture_hash": culture.culture_hash,
        "writer_pattern_id": writer_pattern_id,
        "opening_family_id": opening,
        "sentence_geometry_id": sentence_geometry,
        "organization_geometry_id": layout,
        "connective_id": connective,
        "closing_id": closing,
        "calibration_id": calibration,
        "attention_id": attention,
        "correction_id": culture.correction_protocol_id,
        "selected_operation_ids": selected,
        "effective_voice_signature": effective_voice_signature,
        "effective_geometry_signature": effective_geometry_signature,
        "causal_provenance": (
            ("culture", culture.culture_hash),
            ("persona_state", projection.persona_view.persona_state_hash),
            ("channel_contract_input", projection.capability_id),
            ("catalog", COMMUNICATION_CATALOG_REVISION),
        ),
        "prohibited_inferences": _PROHIBITED,
        "catalog_revision": COMMUNICATION_CATALOG_REVISION,
        "core_revision": COMMUNICATION_CULTURE_CORE_REVISION,
    }
    return IndividualStyleProjection(
        style_id=f"ISTYLE-{digest(payload)[:18]}",
        **payload,
    )

