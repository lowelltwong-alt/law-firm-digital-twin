from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from .case_manifest import EvidenceFamilyCapability
from .hashio import canonical_json, digest
from .persona_state import (
    PERSONA_CORE_REVISION,
    PersonaStateSnapshot,
    RendererPersonaView,
    project_persona_for_renderer,
)


EVIDENCE_CORE_REVISION = "evidence-contracts-g2-v1"
CanonicalStatus = Literal["proposal_only"]


@dataclass(frozen=True)
class FactAssertion:
    world_namespace: str
    matter_namespace: str
    author_id: str
    fact_id: str
    value: str
    source_kind: str
    source_id: str
    learned_day: int

    @property
    def assertion_id(self) -> str:
        return f"ASSERT-{digest(self)[:18]}"


@dataclass(frozen=True)
class ArtifactVersionLineage:
    logical_artifact_id: str
    version_id: str
    revision: int
    parent_version_id: str | None
    parent_content_hash: str | None
    supersession_reason: str | None

    @property
    def lineage_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ArtifactPlan:
    plan_id: str
    world_namespace: str
    matter_namespace: str
    capability_id: str
    capability_revision: str
    family_id: str
    channel_kind: str
    author_id: str
    recipient_ids: tuple[str, ...]
    created_day: int
    allowed_assertions: tuple[FactAssertion, ...]
    required_metadata_keys: tuple[str, ...]
    simulated_target_native_format: str
    responsive: bool
    privileged: bool
    availability: Literal["initial", "discoverable", "withheld_nonresponsive", "missing_or_corrupted"]
    persona_state_id: str
    persona_state_hash: str
    knowledge_frontier_hash: str
    lineage: ArtifactVersionLineage
    purpose_commitment: str
    core_revision: str = EVIDENCE_CORE_REVISION
    synthetic_only: bool = True

    @property
    def plan_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class RendererArtifactProjection:
    projection_id: str
    plan_id: str
    plan_hash: str
    world_namespace: str
    matter_namespace: str
    capability_id: str
    capability_revision: str
    family_id: str
    channel_kind: str
    author_id: str
    recipient_ids: tuple[str, ...]
    created_day: int
    allowed_assertions: tuple[FactAssertion, ...]
    required_metadata_keys: tuple[str, ...]
    simulated_target_native_format: str
    persona_view: RendererPersonaView
    lineage: ArtifactVersionLineage
    core_revision: str
    synthetic_only: bool = True

    @property
    def projection_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class StagedArtifact:
    staged_artifact_id: str
    world_namespace: str
    matter_namespace: str
    plan_id: str
    plan_hash: str
    renderer_projection_hash: str
    capability_id: str
    capability_revision: str
    family_id: str
    author_id: str
    recipient_ids: tuple[str, ...]
    created_day: int
    body: str
    assertions: tuple[FactAssertion, ...]
    metadata: tuple[tuple[str, str], ...]
    simulated_target_native_format: str
    rendered_media_type: str
    lineage: ArtifactVersionLineage
    claimed_content_hash: str
    claimed_lineage_hash: str
    custody_origin_hash: str
    renderer_revision: str
    canonical_status: CanonicalStatus = "proposal_only"
    synthetic_only: bool = True


@dataclass(frozen=True)
class ArtifactValidationFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class ArtifactValidationReport:
    passed: bool
    findings: tuple[ArtifactValidationFinding, ...]
    staged_artifact_hash: str
    validator_revision: str = EVIDENCE_CORE_REVISION


@dataclass(frozen=True)
class LocalArtifactShapeReceipt:
    """Local hash/shape check only; never proves fact authority, lineage, or admission."""
    receipt_id: str
    staged_artifact_id: str
    staged_artifact_hash: str
    plan_hash: str
    renderer_projection_hash: str
    validator_revision: str
    decision: Literal["local_shape_validated_only"]
    authority_validated: Literal[False] = False
    lineage_graph_validated: Literal[False] = False
    canonical_admission: Literal[False] = False

    @property
    def receipt_hash(self) -> str:
        return digest(self)





def _required_metadata(capability: EvidenceFamilyCapability) -> tuple[str, ...]:
    base = {"artifact_id", "created_day", "synthetic"}
    if capability.requires_sender:
        base.add("author_id")
    if capability.requires_recipients:
        base.add("recipient_ids")
    if capability.requires_contract_lineage:
        base.update(("version_id", "lineage_hash"))
    return tuple(sorted(base))


def validate_plan_authority(
    plan: ArtifactPlan,
    persona_state: PersonaStateSnapshot,
    capability: EvidenceFamilyCapability,
) -> tuple[str, ...]:
    errors: list[str] = []
    if capability.recipient_policy_id != "case_scoped_relationship_grant.v1":
        errors.append("recipient_policy_unsupported")
    if capability.revision != plan.capability_revision:
        errors.append("stale_capability_revision")
    if capability.family_id != plan.family_id or capability.capability_id != plan.capability_id:
        errors.append("capability_contract_mismatch")
    if persona_state.world_namespace != plan.world_namespace:
        errors.append("cross_world_persona_state")
    if persona_state.matter_namespace != plan.matter_namespace:
        errors.append("cross_matter_persona_state")
    if persona_state.actor_id != plan.author_id:
        errors.append("persona_author_mismatch")
    if persona_state.role_id not in set(capability.allowed_author_roles):
        errors.append("capability_author_unauthorized")
    if persona_state.as_of_day != plan.created_day:
        errors.append("persona_time_mismatch")
    assertion_ids = {item.assertion_id for item in plan.allowed_assertions}
    if not assertion_ids.issubset(set(persona_state.knowledge_assertion_ids)):
        errors.append("assertion_grant_violation")
    expected_relationships = {
        f"REL-{digest({'world': plan.world_namespace, 'source': plan.author_id, 'target': target})[:16]}"
        for target in plan.recipient_ids
    }
    if not expected_relationships.issubset(set(persona_state.relationship_ids)):
        errors.append("recipient_relationship_unauthorized")
    return tuple(errors)




def build_artifact_plan(
    *,
    world_namespace: str,
    matter_namespace: str,
    capability: EvidenceFamilyCapability,
    author_id: str,
    recipient_ids: Iterable[str],
    created_day: int,
    allowed_assertions: Iterable[FactAssertion],
    persona_state: PersonaStateSnapshot,
    logical_artifact_id: str,
    revision: int = 1,
    parent_artifact: StagedArtifact | None = None,
    parent_projection: RendererArtifactProjection | None = None,
    supersession_reason: str | None = None,
    responsive: bool = True,
    privileged: bool = False,
    availability: Literal["initial", "discoverable", "withheld_nonresponsive", "missing_or_corrupted"] = "discoverable",
    simulated_target_native_format: str = "application/json",
    purpose: str = "synthetic business record",
) -> ArtifactPlan:
    if capability.readiness != "active_g2":
        raise ValueError("evidence_capability_not_active")
    if capability.recipient_policy_id != "case_scoped_relationship_grant.v1":
        raise ValueError("recipient_policy_unsupported")
    if not world_namespace or not matter_namespace:
        raise ValueError("case_namespace_required")
    if persona_state.world_namespace != world_namespace:
        raise ValueError("cross_world_persona_state")
    if persona_state.matter_namespace != matter_namespace:
        raise ValueError("cross_matter_persona_state")
    if persona_state.role_id not in set(capability.allowed_author_roles):
        raise ValueError("capability_author_unauthorized")
    if persona_state.actor_id != author_id:
        raise ValueError("persona_author_mismatch")
    if persona_state.as_of_day != created_day:
        raise ValueError("persona_time_mismatch")
    if simulated_target_native_format not in capability.allowed_native_formats:
        raise ValueError("native_format_not_allowed")
    recipients = tuple(sorted(set(recipient_ids)))
    assertions = tuple(sorted(set(allowed_assertions), key=lambda item: item.assertion_id))
    if any(
        item.world_namespace != world_namespace
        or item.matter_namespace != matter_namespace
        or item.author_id != author_id
        for item in assertions
    ):
        raise ValueError("assertion_scope_mismatch")
    unknown = sorted(
        {item.fact_id for item in assertions} - set(persona_state.knowledge_fact_ids)
    )
    if unknown:
        raise ValueError(f"knowledge_frontier_violation:{unknown}")
    if any(item.learned_day > created_day for item in assertions):
        raise ValueError("future_knowledge_violation")
    ungranted = sorted(
        {item.assertion_id for item in assertions}
        - set(persona_state.knowledge_assertion_ids)
    )
    if ungranted:
        raise ValueError(f"assertion_grant_violation:{ungranted}")
    if capability.requires_sender and not author_id:
        raise ValueError("sender_required")
    if capability.requires_recipients and not recipients:
        raise ValueError("recipients_required")
    expected_relationships = {
        f"REL-{digest({'world': world_namespace, 'source': author_id, 'target': target})[:16]}"
        for target in recipients
    }
    if not expected_relationships.issubset(set(persona_state.relationship_ids)):
        raise ValueError("recipient_relationship_unauthorized")
    if revision == 1 and parent_artifact is not None:
        raise ValueError("initial_version_has_parent")
    if revision == 1 and parent_projection is not None:
        raise ValueError("initial_version_has_parent")
    if revision > 1:
        if parent_artifact is None:
            raise ValueError("parent_artifact_required")
        if parent_projection is None:
            raise ValueError("parent_projection_required")
        if parent_artifact.world_namespace != world_namespace or parent_artifact.matter_namespace != matter_namespace:
            raise ValueError("cross_scope_parent_artifact")
        if parent_artifact.lineage.logical_artifact_id != logical_artifact_id:
            raise ValueError("parent_logical_artifact_mismatch")
        if parent_artifact.lineage.revision != revision - 1:
            raise ValueError("parent_revision_not_contiguous")
        parent_report = validate_staged_artifact(parent_artifact, parent_projection)
        if not parent_report.passed:
            raise ValueError("parent_artifact_validation_failed")
        if parent_artifact.renderer_projection_hash != parent_projection.projection_hash:
            raise ValueError("parent_projection_mismatch")
    lineage = ArtifactVersionLineage(
        logical_artifact_id=logical_artifact_id,
        version_id=f"{logical_artifact_id}-V{revision}",
        revision=revision,
        parent_version_id=parent_artifact.lineage.version_id if parent_artifact else None,
        parent_content_hash=parent_artifact.claimed_content_hash if parent_artifact else None,
        supersession_reason=supersession_reason,
    )
    lineage_errors = validate_version_lineage(lineage)
    if lineage_errors:
        raise ValueError(";".join(lineage_errors))
    plan_id = f"APLAN-{digest({'world': world_namespace, 'logical': logical_artifact_id, 'revision': revision})[:18]}"
    return ArtifactPlan(
        plan_id=plan_id,
        world_namespace=world_namespace,
        matter_namespace=matter_namespace,
        capability_id=capability.capability_id,
        capability_revision=capability.revision,
        family_id=capability.family_id,
        channel_kind=capability.channel_kind,
        author_id=author_id,
        recipient_ids=recipients,
        created_day=created_day,
        allowed_assertions=assertions,
        required_metadata_keys=_required_metadata(capability),
        simulated_target_native_format=simulated_target_native_format,
        responsive=responsive,
        privileged=privileged,
        availability=availability,
        persona_state_id=persona_state.state_id,
        persona_state_hash=persona_state.state_hash,
        knowledge_frontier_hash=digest(
            {
                "world": world_namespace,
                "matter": matter_namespace,
                "actor": author_id,
                "as_of_day": created_day,
                "facts": persona_state.knowledge_fact_ids,
                "assertions": persona_state.knowledge_assertion_ids,
            }
        ),
        lineage=lineage,
        purpose_commitment=digest({"purpose": purpose, "world": world_namespace}),
    )


def build_renderer_projection(
    plan: ArtifactPlan,
    persona_view: RendererPersonaView,
    persona_state: PersonaStateSnapshot,
) -> RendererArtifactProjection:
    if not isinstance(plan, ArtifactPlan):
        raise ValueError("invalid_artifact_plan_type")
    if not isinstance(persona_view, RendererPersonaView):
        raise ValueError("invalid_persona_view_type")
    if not isinstance(persona_state, PersonaStateSnapshot):
        raise ValueError("invalid_persona_state_type")
    if persona_view.world_namespace != plan.world_namespace:
        raise ValueError("cross_world_reference")
    if persona_view.matter_namespace != plan.matter_namespace:
        raise ValueError("cross_matter_reference")
    if persona_view.actor_id != plan.author_id:
        raise ValueError("persona_author_mismatch")
    if persona_view.as_of_day != plan.created_day:
        raise ValueError("persona_time_mismatch")
    if persona_view.persona_state_id != plan.persona_state_id:
        raise ValueError("stale_persona_state")
    if persona_view.persona_state_hash != plan.persona_state_hash:
        raise ValueError("stale_persona_state")
    if persona_view.core_revision != PERSONA_CORE_REVISION:
        raise ValueError("stale_persona_revision")
    if persona_state.state_hash != plan.persona_state_hash:
        raise ValueError("stale_persona_state")
    expected_view = project_persona_for_renderer(
        persona_state,
        allowed_fact_ids=(item.fact_id for item in plan.allowed_assertions),
        allowed_assertion_ids=(item.assertion_id for item in plan.allowed_assertions),
    )
    if persona_view != expected_view:
        raise ValueError("noncanonical_persona_view")
    allowed_fact_ids = {item.fact_id for item in plan.allowed_assertions}
    if not allowed_fact_ids.issubset(persona_view.allowed_fact_ids):
        raise ValueError("knowledge_frontier_violation")
    allowed_assertion_ids = {item.assertion_id for item in plan.allowed_assertions}
    if not allowed_assertion_ids.issubset(persona_view.allowed_assertion_ids):
        raise ValueError("assertion_grant_violation")
    projection_id = f"RPROJ-{digest({'plan': plan.plan_hash, 'persona': persona_view.view_hash})[:18]}"
    return RendererArtifactProjection(
        projection_id=projection_id,
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        world_namespace=plan.world_namespace,
        matter_namespace=plan.matter_namespace,
        capability_id=plan.capability_id,
        capability_revision=plan.capability_revision,
        family_id=plan.family_id,
        channel_kind=plan.channel_kind,
        author_id=plan.author_id,
        recipient_ids=plan.recipient_ids,
        created_day=plan.created_day,
        allowed_assertions=plan.allowed_assertions,
        required_metadata_keys=plan.required_metadata_keys,
        simulated_target_native_format=plan.simulated_target_native_format,
        persona_view=persona_view,
        lineage=plan.lineage,
        core_revision=plan.core_revision,
    )


def _content_commitment(
    projection: RendererArtifactProjection,
    *,
    body: str,
    assertions: tuple[FactAssertion, ...],
    metadata: tuple[tuple[str, str], ...],
) -> str:
    return digest(
        {
            "projection_hash": projection.projection_hash,
            "body": body,
            "assertions": assertions,
            "metadata": metadata,
            "simulated_target_native_format": projection.simulated_target_native_format,
            "lineage": projection.lineage,
        }
    )


def stage_artifact(
    projection: RendererArtifactProjection,
    *,
    body: str,
    assertions: Iterable[FactAssertion],
    metadata: Iterable[tuple[str, str]],
    renderer_revision: str,
) -> StagedArtifact:
    if not isinstance(projection, RendererArtifactProjection):
        raise ValueError("invalid_renderer_projection_type")
    assertions_tuple = tuple(sorted(set(assertions), key=lambda item: item.assertion_id))
    metadata_tuple = tuple(sorted(set(metadata)))
    content_hash = _content_commitment(
        projection,
        body=body,
        assertions=assertions_tuple,
        metadata=metadata_tuple,
    )
    staged_id = f"STAGED-{digest({'projection': projection.projection_hash, 'content': content_hash})[:18]}"
    custody_hash = digest(
        {
            "action": "staged",
            "staged_artifact_id": staged_id,
            "content_hash": content_hash,
            "required_metadata": metadata_tuple,
            "lineage_hash": projection.lineage.lineage_hash,
        }
    )
    staged = StagedArtifact(
        staged_artifact_id=staged_id,
        world_namespace=projection.world_namespace,
        matter_namespace=projection.matter_namespace,
        plan_id=projection.plan_id,
        plan_hash=projection.plan_hash,
        renderer_projection_hash=projection.projection_hash,
        capability_id=projection.capability_id,
        capability_revision=projection.capability_revision,
        family_id=projection.family_id,
        author_id=projection.author_id,
        recipient_ids=projection.recipient_ids,
        created_day=projection.created_day,
        body=body,
        assertions=assertions_tuple,
        metadata=metadata_tuple,
        simulated_target_native_format=projection.simulated_target_native_format,
        rendered_media_type="text/plain",
        lineage=projection.lineage,
        claimed_content_hash=content_hash,
        claimed_lineage_hash=projection.lineage.lineage_hash,
        custody_origin_hash=custody_hash,
        renderer_revision=renderer_revision,
    )
    report = validate_staged_artifact(staged, projection)
    if not report.passed:
        raise ValueError(";".join(item.code for item in report.findings))
    return staged


def validate_version_lineage(lineage: ArtifactVersionLineage) -> tuple[str, ...]:
    errors: list[str] = []
    if lineage.revision < 1:
        errors.append("lineage_revision_invalid")
    if lineage.revision == 1:
        if lineage.parent_version_id or lineage.parent_content_hash or lineage.supersession_reason:
            errors.append("initial_version_has_parent")
    else:
        if not lineage.parent_version_id or not lineage.parent_content_hash:
            errors.append("parent_version_required")
        if not lineage.supersession_reason:
            errors.append("supersession_reason_required")
        if lineage.parent_version_id == lineage.version_id:
            errors.append("lineage_self_parent")
    return tuple(errors)


def validate_staged_artifact(
    staged: StagedArtifact,
    projection: RendererArtifactProjection,
) -> ArtifactValidationReport:
    findings: list[ArtifactValidationFinding] = []

    def add(code: str, message: str) -> None:
        findings.append(ArtifactValidationFinding(code, staged.staged_artifact_id, message))

    if staged.world_namespace != projection.world_namespace:
        add("cross_world_reference", "staged artifact and renderer projection worlds differ")
    if staged.matter_namespace != projection.matter_namespace:
        add("cross_matter_reference", "staged artifact and renderer projection matters differ")
    if staged.plan_id != projection.plan_id or staged.plan_hash != projection.plan_hash:
        add("plan_commitment_mismatch", "plan identity or commitment differs")
    if staged.renderer_projection_hash != projection.projection_hash:
        add("renderer_projection_mismatch", "renderer projection commitment differs")
    if staged.capability_id != projection.capability_id or staged.family_id != projection.family_id:
        add("family_contract_mismatch", "artifact family or capability differs")
    if staged.capability_revision != projection.capability_revision:
        add("stale_capability_revision", "artifact capability revision differs")
    if staged.author_id != projection.author_id:
        add("author_mismatch", "artifact author differs")
    if staged.recipient_ids != projection.recipient_ids:
        add("recipient_mismatch", "artifact recipients differ")
    if staged.created_day != projection.created_day:
        add("artifact_time_mismatch", "artifact time differs")
    if staged.simulated_target_native_format != projection.simulated_target_native_format:
        add("target_native_format_mismatch", "simulated target format differs")
    if staged.rendered_media_type != "text/plain":
        add("rendered_media_type_mismatch", "G2 fixture bytes are text/plain")
    if staged.canonical_status != "proposal_only":
        add("worker_admission_forbidden", "only a future kernel adapter may admit artifacts")
    if not staged.synthetic_only:
        add("synthetic_boundary_missing", "artifact must remain synthetic")
    if not staged.renderer_revision:
        add("renderer_revision_missing", "renderer revision is required")
    if len(staged.body.strip()) < 24:
        add("placeholder_body", "body lacks substantive G2 content")
    lowered = staged.body.lower()
    if any(term in lowered for term in ("lorem ipsum", "todo", "placeholder document")):
        add("placeholder_body", "body contains placeholder language")
    expected_assertions = canonical_json(projection.allowed_assertions)
    observed_assertions = canonical_json(staged.assertions)
    if observed_assertions != expected_assertions:
        expected_ids = {item.assertion_id for item in projection.allowed_assertions}
        observed_ids = {item.assertion_id for item in staged.assertions}
        if observed_ids - expected_ids:
            add("renderer_fact_invention", "renderer added an assertion outside the projection")
        elif expected_ids - observed_ids:
            add("required_assertion_omitted", "renderer omitted an allowed required assertion")
        else:
            add("renderer_fact_mutation", "renderer changed an allowlisted assertion")
    metadata = dict(staged.metadata)
    missing_metadata = sorted(set(projection.required_metadata_keys) - set(metadata))
    if missing_metadata:
        add("required_metadata_missing", f"missing metadata keys {missing_metadata}")
    if len(metadata) != len(staged.metadata):
        add("duplicate_metadata_key", "metadata keys must be unique")
    expected_content_hash = _content_commitment(
        projection,
        body=staged.body,
        assertions=staged.assertions,
        metadata=staged.metadata,
    )
    if staged.claimed_content_hash != expected_content_hash:
        add("content_hash_mismatch", "body, assertion, metadata, or lineage commitment changed")
    expected_staged_id = f"STAGED-{digest({'projection': projection.projection_hash, 'content': expected_content_hash})[:18]}"
    if staged.staged_artifact_id != expected_staged_id:
        add("staged_artifact_id_mismatch", "staged identity is not derived from projection and content")
    if staged.claimed_lineage_hash != staged.lineage.lineage_hash:
        add("lineage_hash_mismatch", "lineage commitment changed")
    if staged.lineage != projection.lineage:
        add("lineage_projection_mismatch", "lineage differs from projection")
    for error in validate_version_lineage(staged.lineage):
        add(error, "version lineage is invalid")
    expected_custody = digest(
        {
            "action": "staged",
            "staged_artifact_id": staged.staged_artifact_id,
            "content_hash": staged.claimed_content_hash,
            "required_metadata": staged.metadata,
            "lineage_hash": staged.claimed_lineage_hash,
        }
    )
    if staged.custody_origin_hash != expected_custody:
        add("custody_hash_mismatch", "custody origin does not authenticate staged bytes")
    return ArtifactValidationReport(
        passed=not findings,
        findings=tuple(findings),
        staged_artifact_hash=digest(staged),
    )


def issue_local_shape_receipt(
    staged: StagedArtifact,
    projection: RendererArtifactProjection,
) -> LocalArtifactShapeReceipt:
    report = validate_staged_artifact(staged, projection)
    if not report.passed:
        raise ValueError("artifact_validation_failed")
    return LocalArtifactShapeReceipt(
        receipt_id=f"ACAND-{digest({'artifact': report.staged_artifact_hash, 'validator': report.validator_revision})[:18]}",
        staged_artifact_id=staged.staged_artifact_id,
        staged_artifact_hash=report.staged_artifact_hash,
        plan_hash=staged.plan_hash,
        renderer_projection_hash=staged.renderer_projection_hash,
        validator_revision=report.validator_revision,
        decision="local_shape_validated_only",
    )


def validate_local_shape_receipt(
    receipt: LocalArtifactShapeReceipt,
    staged: StagedArtifact,
    projection: RendererArtifactProjection,
) -> tuple[str, ...]:
    report = validate_staged_artifact(staged, projection)
    if not report.passed:
        return ("receipt_artifact_not_valid",)
    expected = LocalArtifactShapeReceipt(
        receipt_id=f"ACAND-{digest({'artifact': report.staged_artifact_hash, 'validator': report.validator_revision})[:18]}",
        staged_artifact_id=staged.staged_artifact_id,
        staged_artifact_hash=report.staged_artifact_hash,
        plan_hash=staged.plan_hash,
        renderer_projection_hash=staged.renderer_projection_hash,
        validator_revision=report.validator_revision,
        decision="local_shape_validated_only",
    )
    return () if receipt == expected else ("candidate_receipt_mismatch",)


def validate_lineage_graph(
    plans: Iterable[ArtifactPlan],
    artifacts: Iterable[StagedArtifact],
) -> tuple[str, ...]:
    plans_tuple = tuple(plans)
    artifacts_tuple = tuple(artifacts)
    errors: list[str] = []
    plan_keys = [
        (item.world_namespace, item.matter_namespace, item.lineage.logical_artifact_id, item.lineage.version_id)
        for item in plans_tuple
    ]
    if len(plan_keys) != len(set(plan_keys)):
        errors.append("duplicate_logical_artifact_version")
    version_ids = [item.lineage.version_id for item in plans_tuple]
    if len(version_ids) != len(set(version_ids)):
        errors.append("duplicate_lineage_version_id")
    artifact_by_plan = {item.plan_id: item for item in artifacts_tuple}
    by_logical: dict[tuple[str, str, str], list[ArtifactPlan]] = {}
    for plan in plans_tuple:
        by_logical.setdefault(
            (plan.world_namespace, plan.matter_namespace, plan.lineage.logical_artifact_id),
            [],
        ).append(plan)
    for group in by_logical.values():
        ordered = sorted(group, key=lambda item: item.lineage.revision)
        revisions = [item.lineage.revision for item in ordered]
        if revisions != list(range(1, len(ordered) + 1)):
            errors.append("lineage_revision_gap_or_missing_root")
            continue
        for parent_plan, child_plan in zip(ordered, ordered[1:]):
            parent_artifact = artifact_by_plan.get(parent_plan.plan_id)
            if parent_artifact is None:
                errors.append("lineage_parent_artifact_missing")
                continue
            if child_plan.lineage.parent_version_id != parent_plan.lineage.version_id:
                errors.append("lineage_parent_version_mismatch")
            if child_plan.lineage.parent_content_hash != parent_artifact.claimed_content_hash:
                errors.append("lineage_parent_hash_mismatch")
    return tuple(sorted(set(errors)))




def render_deterministic_g2_fixture(
    projection: RendererArtifactProjection,
) -> StagedArtifact:
    """Provider-free G2 fixture renderer used only to qualify the typed pipeline."""
    assertion_lines = [
        f"{item.fact_id.replace('_', ' ').title()}: {item.value.replace('_', ' ')}."
        for item in projection.allowed_assertions
    ]
    channel_openers = {
        "email": "Synthetic internal email record",
        "hris_record": "Synthetic human-resources record",
        "policy_document": "Synthetic policy record",
        "structured_table": "Synthetic structured business record",
        "calendar": "Synthetic calendar record",
        "litigation_record": "Synthetic litigation intake record",
        "expert_record": "Synthetic expert work record with source limitations",
        "irrelevant_record": "Synthetic ordinary-course nonresponsive record",
    }
    opener = channel_openers.get(projection.channel_kind, "Synthetic business record")
    voice = dict(projection.persona_view.voice_constraints)
    body_parts = [
        opener + ".",
        f"Author role: {projection.persona_view.role_id}; register: {voice.get('register', 'bounded')}.",
        *assertion_lines,
    ]
    if not assertion_lines:
        body_parts.append(
            "This ordinary-course item records a routine administrative communication unrelated to the disputed employment decision."
        )
    body_parts.append(
        "This record is fictional, G2 text-only, and created from an allowlisted renderer projection."
    )
    metadata_values = {
        "artifact_id": projection.lineage.logical_artifact_id,
        "created_day": str(projection.created_day),
        "synthetic": "true",
        "author_id": projection.author_id,
        "recipient_ids": ",".join(projection.recipient_ids),
        "version_id": projection.lineage.version_id,
        "lineage_hash": projection.lineage.lineage_hash,
    }
    metadata = tuple(
        (key, metadata_values[key])
        for key in projection.required_metadata_keys
    )
    return stage_artifact(
        projection,
        body="\n".join(body_parts),
        assertions=projection.allowed_assertions,
        metadata=metadata,
        renderer_revision="deterministic-g2-fixture-renderer-v1",
    )




def detect_staged_conflicts(
    artifacts: Iterable[StagedArtifact],
) -> dict[str, tuple[str, ...]]:
    """Derive incompatible assertion values without receiving sealed conflict labels."""
    items = tuple(artifacts)
    worlds = {item.world_namespace for item in items}
    matters = {item.matter_namespace for item in items}
    if len(worlds) > 1:
        raise ValueError("cross_world_conflict_scan")
    if len(matters) > 1:
        raise ValueError("cross_matter_conflict_scan")
    by_fact: dict[str, dict[str, set[str]]] = {}
    for artifact in items:
        for assertion in artifact.assertions:
            by_fact.setdefault(assertion.fact_id, {}).setdefault(
                assertion.value,
                set(),
            ).add(artifact.staged_artifact_id)
    return {
        fact_id: tuple(
            sorted(
                artifact_id
                for artifact_ids in values.values()
                for artifact_id in artifact_ids
            )
        )
        for fact_id, values in sorted(by_fact.items())
        if len(values) > 1
    }

