from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from .case_manifest import CapabilityRegistry, build_capability_registry
from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
    validate_case_qualification_receipt,
)

from .composition_contracts import (
    COMPOSITION_CORE_REVISION,
    COMPOSITION_LEXICON_REVISION,
    G2_FIDELITY_STATEMENT,
    ChannelCompositionContract,
    CompositionPlan,
    TextCompositionCandidate,
    TextSegmentTrace,
    WritingDispositionProjection,
    build_channel_composition_contracts,
    derive_writing_disposition,
)
from .evidence_contracts import (
    LocalArtifactShapeReceipt,
    RendererArtifactProjection,
    StagedArtifact,
    issue_local_shape_receipt,
    stage_artifact,
    validate_local_shape_receipt,
    validate_staged_artifact,
)
from .hashio import canonical_json, digest


PERSONA_CHANNEL_ADAPTER_REVISION = "persona-channel-adapter-g2-v1"
PERSONA_CHANNEL_VALIDATOR_REVISION = "persona-channel-validator-g2-v1"

_FORBIDDEN_RENDER_TERMS = (
    "sealed_axis_labels",
    "design_labels",
    "target_posture",
    "target_strength",
    "conflict_purpose",
    "evaluator_case_id",
    "evaluation_projection",
    "world_truth",
    "oracle",
    "real_world_prediction",
    "mbti",
    "left-brain",
    "right-brain",
    "class determines",
    "education equals intelligence",
)

_VOICE_OPENINGS = {
    "direct": (
        "Quick update for this synthetic record.",
        "Bottom line first for this synthetic record.",
        "Here is the projected information.",
        "Recording the current projected entry.",
        "Short update for the synthetic file.",
        "Projected status, stated directly.",
    ),
    "contextual": (
        "I am recording the projected context below.",
        "For the synthetic record, the current context follows.",
        "This entry gathers the projected information in one place.",
        "I am documenting the projected status as it presently appears.",
        "The synthetic record below is limited to the projected information.",
        "For context, I have set out the projected entry below.",
    ),
    "formal": (
        "This synthetic entry records only the projected information.",
        "The following is a bounded statement of the projected record.",
        "This text fixture presents the projected material in structured form.",
        "The projected information is stated below without further inference.",
        "This entry is limited to the approved projection.",
        "The following record is source-bounded and synthetic.",
    ),
    "ledger": (
        "Synthetic record summary follows.",
        "Projected entry for reconciliation follows.",
        "Current synthetic record lines follow.",
        "Record-first summary follows.",
        "Projected values are listed below.",
        "Synthetic transaction-style entry follows.",
    ),
    "service": (
        "I have organized the projected information below.",
        "This synthetic entry captures the projected record.",
        "For review, the projected information follows.",
        "I am recording the projected details in order.",
        "The current synthetic entry is set out below.",
        "I have kept this entry to the projected information.",
    ),
}

_VOICE_CLOSINGS = {
    "direct": (
        "End of projected update.",
        "No additional fact is stated.",
        "That is the complete projected entry.",
        "The synthetic update ends here.",
        "No inference is added.",
        "Record complete within this projection.",
    ),
    "contextual": (
        "This entry does not extend beyond the projected information.",
        "I have not added an inference beyond the synthetic projection.",
        "The entry is complete for this bounded record.",
        "No additional factual conclusion is intended.",
        "This concludes the projected context.",
        "The synthetic record is limited accordingly.",
    ),
    "formal": (
        "No opinion or conclusion beyond the projection is expressed.",
        "The record is complete within its stated synthetic limits.",
        "No unprojected proposition is incorporated.",
        "This concludes the bounded synthetic entry.",
        "Further inference is expressly excluded.",
        "The text remains limited to the approved projection.",
    ),
    "ledger": (
        "Synthetic record closed.",
        "No unprojected value posted.",
        "Projected lines complete.",
        "Reconciliation scope complete.",
        "No additional record line.",
        "Entry closed without further inference.",
    ),
    "service": (
        "This completes the projected synthetic record.",
        "Nothing outside the projection has been added.",
        "The bounded entry is complete.",
        "This concludes the synthetic record.",
        "The entry remains limited to the projected details.",
        "No additional factual statement is included.",
    ),
}

_SECTION_TEXT = {
    "scope": "Scope: synthetic process description limited to projected assertions.",
    "process": "Process note: no step is inferred beyond the projected assertions.",
    "known_materials": "Known materials: only the assertion sources identified in the trace.",
    "next_action": "Next action: retain for bounded synthetic review; no legal action is implied.",
    "materials": "Materials considered: only the assertions supplied by the renderer projection.",
    "method": "Method: organize the supplied assertions without adding a factual proposition.",
    "limitations": "Limitation: no conclusion extends beyond the supplied assertions.",
    "bounded_opinion": "Bounded opinion: none beyond the exact projected observations.",
    "ordinary_course_message": "This is an ordinary-course synthetic record with no disputed-event assertion.",
    "nonresponsive_basis": "Nonresponsive basis: the projection supplies no responsive factual assertion.",
    "note": "Narrative note: see the traced assertion entries below.",
    "notes": "Notes: this text fixture adds no event detail beyond the projected status.",
    "closing": "Closing: bounded synthetic entry.",
}


@dataclass(frozen=True)
class CompositionFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class CompositionValidationReport:
    passed: bool
    findings: tuple[CompositionFinding, ...]
    candidate_hash: str
    validator_revision: str = PERSONA_CHANNEL_VALIDATOR_REVISION


@dataclass(frozen=True)
class PersonaChannelRenderReceipt:
    receipt_id: str
    renderer_projection_hash: str
    channel_contract_hash: str
    disposition_hash: str
    organization_culture_hash: str
    individual_style_hash: str
    effective_geometry_signature: str
    composition_plan_hash: str
    candidate_hash: str
    staged_artifact_hash: str
    local_shape_receipt_hash: str
    adapter_revision: str
    composition_validated: Literal[True]
    factual_authority_validated: Literal[False] = False
    lineage_graph_validated: Literal[False] = False
    canonical_admission: Literal[False] = False

    @property
    def receipt_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class PersonaChannelRenderBundle:
    contract: ChannelCompositionContract
    disposition: WritingDispositionProjection
    plan: CompositionPlan
    candidate: TextCompositionCandidate
    staged_artifact: StagedArtifact
    local_shape_receipt: LocalArtifactShapeReceipt
    render_receipt: PersonaChannelRenderReceipt

    @property
    def bundle_hash(self) -> str:
        return digest(self)


def _voice_family(disposition: WritingDispositionProjection) -> str:
    controls = dict(disposition.style_controls)
    opening_family = controls.get("opening_family", "")
    by_operation = {
        "opening_direct": "direct",
        "opening_contextual": "contextual",
        "opening_formal": "formal",
        "opening_ledger": "ledger",
        "opening_service": "service",
    }
    if opening_family in by_operation:
        return by_operation[opening_family]
    register = controls.get("register", "")
    if "plain" in register:
        return "direct"
    if "business" in register:
        return "contextual"
    if "financial" in register:
        return "ledger"
    if "warm" in register:
        return "service"
    return "formal"


def _ordered_assertion_ids(
    projection: RendererArtifactProjection,
    disposition: WritingDispositionProjection,
) -> tuple[str, ...]:
    controls = dict(disposition.style_controls)
    organization = controls.get("organization", "")
    assertions = list(projection.allowed_assertions)
    if "chronological" in organization or "date" in organization:
        assertions.sort(key=lambda item: (item.learned_day, item.assertion_id))
    elif "amount" in organization or "entity" in organization:
        assertions.sort(key=lambda item: (item.fact_id, item.assertion_id))
    elif "bottom line" in organization:
        assertions.sort(key=lambda item: (item.fact_id, item.assertion_id), reverse=True)
    return tuple(item.assertion_id for item in assertions)


def build_composition_plan(
    projection: RendererArtifactProjection,
    contract: ChannelCompositionContract,
    disposition: WritingDispositionProjection,
) -> CompositionPlan:
    if projection.capability_id != contract.capability_id:
        raise ValueError("composition_capability_mismatch")
    if projection.capability_revision != contract.capability_revision:
        raise ValueError("composition_capability_revision_mismatch")
    if projection.channel_kind != contract.channel_kind:
        raise ValueError("composition_channel_mismatch")
    if projection.persona_view.persona_state_hash != disposition.source_persona_state_hash:
        raise ValueError("composition_persona_state_mismatch")
    if projection.simulated_target_native_format not in contract.allowed_target_native_formats:
        raise ValueError("composition_target_format_not_allowed")
    assertion_order = _ordered_assertion_ids(projection, disposition)
    section_plan = tuple(
        (
            section,
            assertion_order if section == contract.assertion_section else (),
        )
        for section in contract.required_sections
    )
    style_operations = tuple(
        item
        for item in disposition.allowed_style_operations
        if item in contract.permitted_style_operations
    )
    allowed_stream_payload = {
        "world": projection.world_namespace,
        "matter": projection.matter_namespace,
        "logical_artifact": projection.lineage.logical_artifact_id,
        "version": projection.lineage.version_id,
        "author": projection.author_id,
        "recipients": projection.recipient_ids,
        "day": projection.created_day,
        "assertions": assertion_order,
        "contract": contract.contract_hash,
        "allowed_disposition": {
            "voice_signature": disposition.voice_signature,
            "style_controls": disposition.style_controls,
            "memory_controls": disposition.memory_controls,
            "audience_mode": disposition.audience_mode,
            "channel_compatibility": disposition.channel_compatibility,
            "allowed_style_operations": disposition.allowed_style_operations,
        },
        "lexicon": COMPOSITION_LEXICON_REVISION,
    }
    stream_key = digest(allowed_stream_payload)
    variant_index = int(stream_key[:8], 16) % 6
    voice_family = _voice_family(disposition)
    selected_blocks = (
        f"{contract.channel_kind}.opening.{voice_family}.{variant_index}",
        f"{contract.channel_kind}.closing.{voice_family}.{variant_index}",
        *(
            f"{contract.channel_kind}.section.{section}"
            for section in contract.required_sections
        ),
        f"{contract.channel_kind}.disclosure",
    )
    if not set(selected_blocks).issubset(contract.permitted_nonassertive_block_ids):
        raise ValueError("composition_nonassertive_block_not_permitted")
    payload = {
        "renderer_projection_hash": projection.projection_hash,
        "channel_contract_hash": contract.contract_hash,
        "writing_disposition_hash": disposition.disposition_hash,
        "assertion_order": assertion_order,
        "section_plan": section_plan,
        "style_operations": style_operations,
        "nonassertive_block_ids": selected_blocks,
        "variant_id": f"V{variant_index}",
        "deterministic_stream_key": stream_key,
        "lexicon_revision": COMPOSITION_LEXICON_REVISION,
        "prohibited_inferences": disposition.prohibited_inferences,
        "core_revision": COMPOSITION_CORE_REVISION,
    }
    return CompositionPlan(
        plan_id=f"CPLAN-{digest(payload)[:18]}",
        **payload,
    )


def _humanize(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").split())


def _segment(
    *,
    section_id: str,
    rendered_text: str,
    function: Literal["assertion", "nonassertive", "metadata_label"],
    assertion_ids: Iterable[str] = (),
    style_operation_ids: Iterable[str] = (),
) -> TextSegmentTrace:
    payload = {
        "section_id": section_id,
        "rendered_text": rendered_text,
        "function": function,
        "assertion_ids": tuple(assertion_ids),
        "style_operation_ids": tuple(style_operation_ids),
    }
    return TextSegmentTrace(
        segment_id=f"TSEG-{digest(payload)[:18]}",
        **payload,
    )


def _nonassertive_text(block_id: str, variant_index: int) -> str:
    pieces = block_id.split(".")
    if len(pieces) >= 4 and pieces[1] == "opening":
        return _VOICE_OPENINGS[pieces[2]][variant_index]
    if len(pieces) >= 4 and pieces[1] == "closing":
        return _VOICE_CLOSINGS[pieces[2]][variant_index]
    if len(pieces) >= 3 and pieces[1] == "section":
        section = ".".join(pieces[2:])
        return _SECTION_TEXT.get(
            section,
            f"{_humanize(section).title()}: projection-bounded synthetic section.",
        )
    if pieces[-1] == "disclosure":
        return G2_FIDELITY_STATEMENT
    raise ValueError(f"unknown_nonassertive_block:{block_id}")


def _field_line(
    field_name: str,
    projection: RendererArtifactProjection,
) -> str:
    exact_values = {
        "author_id": projection.author_id,
        "organizer_id": projection.author_id,
        "expert_id": projection.author_id,
        "recipients": ", ".join(projection.recipient_ids) or "[none]",
        "invitees": ", ".join(projection.recipient_ids) or "[none]",
        "created_at": f"synthetic day {projection.created_day}",
        "sent_at": f"synthetic day {projection.created_day}",
        "starts_at": f"synthetic day {projection.created_day}",
        "effective_at": f"synthetic day {projection.created_day}",
        "document_type": projection.channel_kind,
    }
    value = exact_values.get(
        field_name,
        "[projection-bound field; see traced assertion section]",
    )
    return f"{_humanize(field_name).title()}: {value}"


def _assertion_text(assertion: object, *, compact: bool) -> str:
    fact_id = _humanize(getattr(assertion, "fact_id"))
    value = _humanize(getattr(assertion, "value"))
    source_kind = _humanize(getattr(assertion, "source_kind"))
    source_id = getattr(assertion, "source_id")
    learned_day = getattr(assertion, "learned_day")
    if compact:
        return (
            f"{fact_id}: {value} | source {source_kind} / {source_id} "
            f"| learned synthetic day {learned_day}"
        )
    return (
        f"Projected fact {fact_id} has value {value}. "
        f"Its supplied source is {source_kind} {source_id}, and it was "
        f"learned on synthetic day {learned_day}."
    )


def compose_text_candidate(
    projection: RendererArtifactProjection,
    contract: ChannelCompositionContract,
    disposition: WritingDispositionProjection,
    plan: CompositionPlan,
) -> TextCompositionCandidate:
    if plan.renderer_projection_hash != projection.projection_hash:
        raise ValueError("composition_plan_projection_mismatch")
    if plan.channel_contract_hash != contract.contract_hash:
        raise ValueError("composition_plan_contract_mismatch")
    if plan.writing_disposition_hash != disposition.disposition_hash:
        raise ValueError("composition_plan_disposition_mismatch")
    assertions = {item.assertion_id: item for item in projection.allowed_assertions}
    if set(plan.assertion_order) != set(assertions):
        raise ValueError("composition_plan_assertion_scope_mismatch")
    variant_index = int(plan.variant_id[1:])
    opening_id = next(
        item for item in plan.nonassertive_block_ids if ".opening." in item
    )
    closing_id = next(
        item for item in plan.nonassertive_block_ids if ".closing." in item
    )
    disclosure_id = next(
        item for item in plan.nonassertive_block_ids if item.endswith(".disclosure")
    )
    compact = "compact_geometry" in plan.style_operations
    segments: list[TextSegmentTrace] = []
    controls = dict(disposition.style_controls)
    sentence_geometry = controls["sentence_geometry"]
    layout = controls["organization_geometry"]
    for section_id, assertion_ids in plan.section_plan:
        if sentence_geometry == "geometry_compact_lines":
            heading = f"{_humanize(section_id).upper()}:"
        elif sentence_geometry == "geometry_short_paragraph":
            heading = f"{_humanize(section_id).title()} ?"
        else:
            heading = f"[{_humanize(section_id).upper()}]"
        heading_segment = _segment(
            section_id=section_id,
            rendered_text=heading,
            function="metadata_label",
            style_operation_ids=disposition.writer_operation_ids,
        )
        if section_id == contract.required_sections[0]:
            opening_segment = _segment(
                section_id=section_id,
                rendered_text=_nonassertive_text(opening_id, variant_index),
                function="nonassertive",
                style_operation_ids=plan.style_operations,
            )
            record_reference = digest(
                {
                    "world": projection.world_namespace,
                    "matter": projection.matter_namespace,
                    "logical_artifact": projection.lineage.logical_artifact_id,
                }
            )[:12]
            record_segment = _segment(
                section_id=section_id,
                rendered_text=f"Synthetic record reference: {record_reference}",
                function="metadata_label",
                style_operation_ids=disposition.writer_operation_ids,
            )
            field_lines = tuple(
                _field_line(field_name, projection)
                for field_name in contract.required_field_names
            )
            if sentence_geometry == "geometry_compact_lines":
                field_segments = (
                    _segment(
                        section_id=section_id,
                        rendered_text=" | ".join(field_lines),
                        function="metadata_label",
                        style_operation_ids=disposition.writer_operation_ids,
                    ),
                )
            elif sentence_geometry == "geometry_short_paragraph":
                midpoint = max(1, (len(field_lines) + 1) // 2)
                field_segments = tuple(
                    _segment(
                        section_id=section_id,
                        rendered_text="\n".join(chunk),
                        function="metadata_label",
                        style_operation_ids=disposition.writer_operation_ids,
                    )
                    for chunk in (
                        field_lines[:midpoint],
                        field_lines[midpoint:],
                    )
                    if chunk
                )
            else:
                field_segments = tuple(
                    _segment(
                        section_id=section_id,
                        rendered_text=field_line,
                        function="metadata_label",
                        style_operation_ids=disposition.writer_operation_ids,
                    )
                    for field_line in field_lines
                )
            if layout == "layout_fields_first":
                segments.extend(
                    (record_segment, *field_segments, heading_segment, opening_segment)
                )
            elif layout == "layout_record_first":
                segments.extend(
                    (heading_segment, record_segment, *field_segments, opening_segment)
                )
            else:
                segments.extend(
                    (heading_segment, opening_segment, record_segment, *field_segments)
                )
        else:
            segments.append(heading_segment)
        if assertion_ids:
            for assertion_id in assertion_ids:
                segments.append(
                    _segment(
                        section_id=section_id,
                        rendered_text=_assertion_text(
                            assertions[assertion_id],
                            compact=compact,
                        ),
                        function="assertion",
                        assertion_ids=(assertion_id,),
                        style_operation_ids=plan.style_operations,
                    )
                )
        elif section_id not in {
            contract.required_sections[0],
            "disclosure",
            "closing",
        }:
            block_id = f"{contract.channel_kind}.section.{section_id}"
            segments.append(
                _segment(
                    section_id=section_id,
                    rendered_text=_nonassertive_text(block_id, variant_index),
                    function="nonassertive",
                )
            )
        if section_id == "closing":
            segments.append(
                _segment(
                    section_id=section_id,
                    rendered_text=_nonassertive_text(closing_id, variant_index),
                    function="nonassertive",
                    style_operation_ids=plan.style_operations,
                )
            )
        if section_id == "disclosure":
            if "closing" not in contract.required_sections:
                segments.append(
                    _segment(
                        section_id=section_id,
                        rendered_text=_nonassertive_text(
                            closing_id,
                            variant_index,
                        ),
                        function="nonassertive",
                        style_operation_ids=plan.style_operations,
                    )
                )
            segments.append(
                _segment(
                    section_id=section_id,
                    rendered_text=_nonassertive_text(
                        disclosure_id,
                        variant_index,
                    ),
                    function="nonassertive",
                )
            )
    body = "\n".join(item.rendered_text for item in segments)
    payload = {
        "renderer_projection_hash": projection.projection_hash,
        "composition_plan_hash": plan.plan_hash,
        "contract_hash": contract.contract_hash,
        "disposition_hash": disposition.disposition_hash,
        "rendered_media_type": "text/plain",
        "simulated_target_native_format": projection.simulated_target_native_format,
        "body": body,
        "segments": tuple(segments),
        "adapter_revision": PERSONA_CHANNEL_ADAPTER_REVISION,
        "provider_class": "deterministic_fixture",
        "synthetic_only": True,
        "noncanonical": True,
    }
    return TextCompositionCandidate(
        candidate_id=f"TCAND-{digest(payload)[:18]}",
        **payload,
    )


def validate_text_composition_candidate(
    projection: RendererArtifactProjection,
    contract: ChannelCompositionContract,
    disposition: WritingDispositionProjection,
    plan: CompositionPlan,
    candidate: TextCompositionCandidate,
) -> CompositionValidationReport:
    findings: list[CompositionFinding] = []

    def add(code: str, message: str) -> None:
        findings.append(CompositionFinding(code, candidate.candidate_id, message))

    try:
        expected_plan = build_composition_plan(projection, contract, disposition)
        if plan != expected_plan:
            add("noncanonical_composition_plan", "composition plan is not reproducible")
        expected = compose_text_candidate(
            projection,
            contract,
            disposition,
            expected_plan,
        )
        if candidate != expected:
            add("noncanonical_composition_candidate", "candidate is not reproducible")
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        add("composition_replay_failed", str(exc))
    if candidate.body != "\n".join(item.rendered_text for item in candidate.segments):
        add("body_segment_mismatch", "body does not exactly match its segment trace")
    observed: list[str] = []
    expected_assertions = {
        item.assertion_id: item for item in projection.allowed_assertions
    }
    for segment in candidate.segments:
        if segment.function == "assertion":
            if len(segment.assertion_ids) != 1:
                add("assertion_trace_cardinality", "assertion segment must trace one assertion")
                continue
            assertion_id = segment.assertion_ids[0]
            observed.append(assertion_id)
            assertion = expected_assertions.get(assertion_id)
            if assertion is None:
                add("renderer_fact_invention", "trace contains an unauthorized assertion")
            elif segment.rendered_text != _assertion_text(
                assertion,
                compact="compact_geometry" in plan.style_operations,
            ):
                add("renderer_fact_mutation", "assertion text is not the canonical rendering")
        elif segment.assertion_ids:
            add("nonassertive_trace_violation", "nonassertive segment cites assertions")
    if sorted(observed) != sorted(expected_assertions):
        add("assertion_coverage_mismatch", "assertions must appear exactly once")
    section_ids = {item.section_id for item in candidate.segments}
    missing_sections = sorted(set(contract.required_sections) - section_ids)
    if missing_sections:
        add("required_section_missing", f"missing sections {missing_sections}")
    lowered = candidate.body.lower()
    for term in _FORBIDDEN_RENDER_TERMS:
        if term in lowered:
            add("forbidden_context_leak", f"forbidden term present: {term}")
    for field_name in contract.required_field_names:
        label = f"{_humanize(field_name).title()}:"
        if label not in candidate.body:
            add("required_field_missing", f"missing field {field_name}")
    if candidate.rendered_media_type != "text/plain":
        add("rendered_media_type_mismatch", "G2 candidate must be text/plain")
    if candidate.simulated_target_native_format not in contract.allowed_target_native_formats:
        add("target_native_format_not_allowed", "target format is outside contract")
    if not candidate.synthetic_only or not candidate.noncanonical:
        add("boundary_flag_missing", "candidate must be synthetic and noncanonical")
    return CompositionValidationReport(
        passed=not findings,
        findings=tuple(findings),
        candidate_hash=candidate.candidate_hash,
    )


def _staging_metadata(
    projection: RendererArtifactProjection,
    candidate: TextCompositionCandidate,
) -> tuple[tuple[str, str], ...]:
    values = {
        "artifact_id": projection.lineage.logical_artifact_id,
        "created_day": str(projection.created_day),
        "synthetic": "true",
        "author_id": projection.author_id,
        "recipient_ids": canonical_json(projection.recipient_ids),
        "version_id": projection.lineage.version_id,
        "lineage_hash": projection.lineage.lineage_hash,
    }
    metadata = [(key, values[key]) for key in projection.required_metadata_keys]
    metadata.extend(
        (
            ("composition_candidate_hash", candidate.candidate_hash),
            ("composition_core_revision", COMPOSITION_CORE_REVISION),
            ("composition_fidelity", "G2_text_plain_noncanonical"),
        )
    )
    return tuple(metadata)


def render_unqualified_persona_channel_g2_fixture(
    projection: RendererArtifactProjection,
    registry: CapabilityRegistry | None = None,
    presentation_scope_commitment: str | None = None,
) -> PersonaChannelRenderBundle:
    registry = registry or build_capability_registry()
    contract = build_channel_composition_contracts(registry)[projection.capability_id]
    disposition = derive_writing_disposition(
        projection, presentation_scope_commitment
    )
    plan = build_composition_plan(projection, contract, disposition)
    candidate = compose_text_candidate(projection, contract, disposition, plan)
    report = validate_text_composition_candidate(
        projection,
        contract,
        disposition,
        plan,
        candidate,
    )
    if not report.passed:
        raise ValueError(
            "composition_validation_failed:"
            + ",".join(item.code for item in report.findings)
        )
    staged = stage_artifact(
        projection,
        body=candidate.body,
        assertions=projection.allowed_assertions,
        metadata=_staging_metadata(projection, candidate),
        renderer_revision=PERSONA_CHANNEL_ADAPTER_REVISION,
    )
    local_receipt = issue_local_shape_receipt(staged, projection)
    receipt_payload = {
        "renderer_projection_hash": projection.projection_hash,
        "channel_contract_hash": contract.contract_hash,
        "disposition_hash": disposition.disposition_hash,
        "composition_plan_hash": plan.plan_hash,
        "candidate_hash": candidate.candidate_hash,
        "staged_artifact_hash": digest(staged),
        "organization_culture_hash": disposition.organization_culture_hash,
        "individual_style_hash": disposition.individual_style_hash,
        "effective_geometry_signature": disposition.effective_geometry_signature,
        "local_shape_receipt_hash": local_receipt.receipt_hash,
        "adapter_revision": PERSONA_CHANNEL_ADAPTER_REVISION,
        "composition_validated": True,
        "factual_authority_validated": False,
        "lineage_graph_validated": False,
        "canonical_admission": False,
    }
    render_receipt = PersonaChannelRenderReceipt(
        receipt_id=f"PCRECEIPT-{digest(receipt_payload)[:18]}",
        **receipt_payload,
    )
    return PersonaChannelRenderBundle(
        contract=contract,
        disposition=disposition,
        plan=plan,
        candidate=candidate,
        staged_artifact=staged,
        local_shape_receipt=local_receipt,
        render_receipt=render_receipt,
    )


def validate_unqualified_persona_channel_bundle(
    projection: RendererArtifactProjection,
    bundle: PersonaChannelRenderBundle,
    registry: CapabilityRegistry | None = None,
    presentation_scope_commitment: str | None = None,
) -> tuple[str, ...]:
    errors: list[str] = []
    try:
        expected = render_unqualified_persona_channel_g2_fixture(
            projection,
            registry,
            presentation_scope_commitment,
        )
        if bundle != expected:
            errors.append("noncanonical_persona_channel_bundle")
    except (KeyError, StopIteration, TypeError, ValueError):
        errors.append("persona_channel_replay_failed")
    if not validate_staged_artifact(bundle.staged_artifact, projection).passed:
        errors.append("staged_artifact_invalid")
    if validate_local_shape_receipt(
        bundle.local_shape_receipt,
        bundle.staged_artifact,
        projection,
    ):
        errors.append("local_shape_receipt_invalid")
    if bundle.render_receipt.factual_authority_validated:
        errors.append("receipt_authority_overclaim")
    if bundle.render_receipt.lineage_graph_validated:
        errors.append("receipt_lineage_overclaim")
    if bundle.render_receipt.canonical_admission:
        errors.append("receipt_admission_overclaim")
    return tuple(sorted(set(errors)))


def render_unqualified_persona_channel_batch(
    projections: Iterable[RendererArtifactProjection],
    registry: CapabilityRegistry | None = None,
) -> tuple[PersonaChannelRenderBundle, ...]:
    registry = registry or build_capability_registry()
    return tuple(
        render_unqualified_persona_channel_g2_fixture(projection, registry)
        for projection in projections
    )


@dataclass(frozen=True)
class QualifiedPersonaChannelRenderBundle:
    compilation_id: str
    compilation_hash: str
    qualification_receipt_hash: str
    projection_index: int
    source_projection_hash: str
    local_bundle: PersonaChannelRenderBundle
    qualification_boundary_revision: str = "qualified-composition-boundary-g2-v1"

    @property
    def qualified_bundle_hash(self) -> str:
        return digest(self)

    @property
    def contract(self) -> ChannelCompositionContract:
        return self.local_bundle.contract

    @property
    def disposition(self) -> WritingDispositionProjection:
        return self.local_bundle.disposition

    @property
    def plan(self) -> CompositionPlan:
        return self.local_bundle.plan

    @property
    def candidate(self) -> TextCompositionCandidate:
        return self.local_bundle.candidate

    @property
    def staged_artifact(self) -> StagedArtifact:
        return self.local_bundle.staged_artifact

    @property
    def local_shape_receipt(self) -> LocalArtifactShapeReceipt:
        return self.local_bundle.local_shape_receipt

    @property
    def render_receipt(self) -> PersonaChannelRenderReceipt:
        return self.local_bundle.render_receipt


def _render_after_case_qualification(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    projection_index: int,
    registry: CapabilityRegistry,
) -> QualifiedPersonaChannelRenderBundle:
    if not isinstance(projection_index, int):
        raise ValueError("projection_index_invalid")
    if projection_index < 0 or projection_index >= len(
        compilation.renderer_projections
    ):
        raise ValueError("projection_index_invalid")
    projection = compilation.renderer_projections[projection_index]
    local_bundle = render_unqualified_persona_channel_g2_fixture(
        projection,
        registry,
        compilation.presentation_scope_commitment,
    )
    return QualifiedPersonaChannelRenderBundle(
        compilation_id=compilation.compilation_id,
        compilation_hash=compilation.compilation_hash,
        qualification_receipt_hash=qualification_receipt.receipt_hash,
        projection_index=projection_index,
        source_projection_hash=projection.projection_hash,
        local_bundle=local_bundle,
    )



def render_persona_channel_g2_fixture(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    projection_index: int,
    registry: CapabilityRegistry | None = None,
) -> QualifiedPersonaChannelRenderBundle:
    """Render only a projection reselected from a fully qualified compilation."""
    registry = registry or build_capability_registry()
    if not isinstance(compilation, CaseCompilation):
        raise ValueError("case_compilation_type_invalid")
    if not isinstance(qualification_receipt, CaseCompilationQualificationReceipt):
        raise ValueError("case_qualification_receipt_type_invalid")
    if not validate_case_qualification_receipt(
        qualification_receipt,
        compilation,
        registry,
    ):
        raise ValueError("case_qualification_receipt_invalid")
    return _render_after_case_qualification(
        compilation,
        qualification_receipt,
        projection_index,
        registry,
    )


def validate_persona_channel_bundle(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    bundle: QualifiedPersonaChannelRenderBundle,
    registry: CapabilityRegistry | None = None,
) -> tuple[str, ...]:
    registry = registry or build_capability_registry()
    errors: list[str] = []
    if not isinstance(compilation, CaseCompilation):
        return ("case_compilation_type_invalid",)
    if not isinstance(qualification_receipt, CaseCompilationQualificationReceipt):
        return ("case_qualification_receipt_type_invalid",)
    if not isinstance(bundle, QualifiedPersonaChannelRenderBundle):
        return ("qualified_bundle_type_invalid",)
    if not validate_case_qualification_receipt(
        qualification_receipt,
        compilation,
        registry,
    ):
        errors.append("case_qualification_receipt_invalid")
        return tuple(errors)
    if bundle.compilation_id != compilation.compilation_id:
        errors.append("qualified_compilation_id_mismatch")
    if bundle.compilation_hash != compilation.compilation_hash:
        errors.append("qualified_compilation_hash_mismatch")
    if bundle.qualification_receipt_hash != qualification_receipt.receipt_hash:
        errors.append("qualified_receipt_hash_mismatch")
    if bundle.projection_index < 0 or bundle.projection_index >= len(
        compilation.renderer_projections
    ):
        errors.append("qualified_projection_index_invalid")
        return tuple(sorted(set(errors)))
    projection = compilation.renderer_projections[bundle.projection_index]
    if bundle.source_projection_hash != projection.projection_hash:
        errors.append("qualified_projection_hash_mismatch")
    errors.extend(
        validate_unqualified_persona_channel_bundle(
            projection,
            bundle.local_bundle,
            registry,
            compilation.presentation_scope_commitment,
        )
    )
    try:
        expected = _render_after_case_qualification(
            compilation,
            qualification_receipt,
            bundle.projection_index,
            registry,
        )
        if bundle != expected:
            errors.append("noncanonical_qualified_persona_channel_bundle")
    except (KeyError, TypeError, ValueError):
        errors.append("qualified_persona_channel_replay_failed")
    return tuple(sorted(set(errors)))


def render_persona_channel_batch(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    registry: CapabilityRegistry | None = None,
) -> tuple[QualifiedPersonaChannelRenderBundle, ...]:
    registry = registry or build_capability_registry()
    if not isinstance(compilation, CaseCompilation):
        raise ValueError("case_compilation_type_invalid")
    if not isinstance(qualification_receipt, CaseCompilationQualificationReceipt):
        raise ValueError("case_qualification_receipt_type_invalid")
    if not validate_case_qualification_receipt(
        qualification_receipt,
        compilation,
        registry,
    ):
        raise ValueError("case_qualification_receipt_invalid")
    return tuple(
        _render_after_case_qualification(
            compilation,
            qualification_receipt,
            projection_index,
            registry,
        )
        for projection_index in range(len(compilation.renderer_projections))
    )



def validate_persona_channel_batch(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    bundles: Iterable[QualifiedPersonaChannelRenderBundle],
    registry: CapabilityRegistry | None = None,
) -> tuple[str, ...]:
    registry = registry or build_capability_registry()
    observed = tuple(bundles)
    if not validate_case_qualification_receipt(
        qualification_receipt,
        compilation,
        registry,
    ):
        return ("case_qualification_receipt_invalid",)
    try:
        expected = render_persona_channel_batch(
            compilation,
            qualification_receipt,
            registry,
        )
    except ValueError:
        return ("qualified_persona_channel_batch_replay_failed",)
    if observed != expected:
        return ("noncanonical_qualified_persona_channel_batch",)
    return ()

