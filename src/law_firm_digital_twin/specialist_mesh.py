from __future__ import annotations

from collections import Counter
from typing import Sequence

from .case_manifest import (
    CapabilityRegistry,
    CaseFamilyManifest,
    EvidenceFamilyCapability,
    SpecialistCapability,
)
from .evidence_contracts import (
    ArtifactPlan,
    LocalArtifactShapeReceipt,
    RendererArtifactProjection,
    StagedArtifact,
    build_renderer_projection,
)
from .hashio import digest
from .persona_state import PersonaStateSnapshot
from .specialist_mesh_contracts import (
    SPECIALIST_MESH_REVISION,
    ArtifactMeshLocalReceipt,
    ArtifactMeshValidationFinding,
    ArtifactMeshValidationReport,
    ArtifactProductionManifest,
    EvidenceDomainPack,
    SpecialistAssignment,
)


PLANNER_ID = "specialist.case_type_evidence_architect.v1"
RENDERER_ID = "adapter.artifact_renderer.v1"
COMMON_CHECKERS = (
    "specialist.continuity_custody_checker.v1",
    "specialist.domain_plausibility_checker.v1",
    "specialist.document_fidelity_checker.v1",
)
VOICE_CHECKER_ID = "specialist.voice_representation_checker.v1"
WRITER_BY_FAMILY = {
    "employment_litigation": "specialist.employment_intake_record_writer.v1",
    "employment_policy": "specialist.contract_policy_specialist.v1",
    "employment_expert": "specialist.expert_witness_builder.v1",
    "employment_email": "specialist.employment_business_record_writer.v1",
    "employment_hr_record": "specialist.employment_business_record_writer.v1",
    "employment_payroll": "specialist.employment_business_record_writer.v1",
    "employment_calendar": "specialist.employment_business_record_writer.v1",
    "employment_noise": "specialist.employment_business_record_writer.v1",
}
EXCLUDED_INPUT_PLANES = (
    "sealed_case_state",
    "evaluation_projection",
    "source_blueprint",
    "full_case_compilation",
    "raw_private_sources",
    "oracle_or_design_labels",
)


def build_domain_pack(
    family: CaseFamilyManifest,
    registry: CapabilityRegistry,
) -> EvidenceDomainPack:
    evidence_ids = tuple(
        sorted(
            item.capability_id
            for item in registry.evidence_capabilities
            if item.family_id in family.required_evidence_capabilities
        )
    )
    readiness = "active_g2" if family.readiness == "active_g2" else "design_only"
    return EvidenceDomainPack(
        pack_id=f"domain-pack.{family.family_id}.v1",
        revision="1",
        case_family_id=family.family_id,
        case_family_manifest_hash=family.manifest_hash,
        readiness=readiness,
        evidence_capability_ids=evidence_ids,
        expertise_topics=tuple(sorted((*family.fact_domains, *family.expert_domains))),
        required_validator_ids=(
            "validate_domain_scope",
            "validate_capability_coverage",
            "validate_projection_separation",
        ),
        protected_fixture_id=f"fixture.domain-pack.{family.family_id}.v1",
        activation_gate=family.activation_gate,
    )


def _assignment(
    capability_id: str,
    phase: str,
    specialists: dict[str, SpecialistCapability],
    plan_hash: str,
    *,
    independent_of: tuple[str, ...] = (),
) -> SpecialistAssignment:
    capability = specialists.get(capability_id)
    if capability is None:
        raise ValueError(f"missing_specialist_capability:{capability_id}")
    expected_kind = "generator" if phase == "writer" else phase
    if capability.kind != expected_kind:
        raise ValueError(f"specialist_phase_mismatch:{capability_id}:{phase}")
    inputs = {
        "planner": (
            "case_family_manifest_commitment",
            "evidence_capability_commitment",
            "artifact_plan_commitment",
        ),
        "writer": (
            "artifact_plan_commitment",
            "renderer_persona_view_commitment",
            "knowledge_frontier_commitment",
            "authority_frontier_commitment",
        ),
        "renderer": (
            "renderer_artifact_projection_commitment",
            "writer_proposal_commitment",
        ),
        "checker": (
            "staged_artifact_commitment",
            "artifact_production_manifest_commitment",
        ),
    }[phase]
    outputs = {
        "planner": ("bounded_artifact_work_order",),
        "writer": ("staged_artifact_proposal", "assertion_set_proposal"),
        "renderer": ("deterministic_renderer_candidate",),
        "checker": ("immutable_findings", "abstentions"),
    }[phase]
    payload = {
        "plan_hash": plan_hash,
        "phase": phase,
        "capability_id": capability_id,
        "revision": capability.revision,
        "inputs": inputs,
        "outputs": outputs,
        "independent_of": independent_of,
        "mesh_revision": SPECIALIST_MESH_REVISION,
    }
    return SpecialistAssignment(
        assignment_id=f"MESH-ASG-{digest(payload)[:18]}",
        phase=phase,  # type: ignore[arg-type]
        specialist_capability_id=capability_id,
        specialist_revision=capability.revision,
        specialist_capability_contract_hash=digest(capability),
        capability_classification=capability.classification,
        input_contract_ids=inputs,
        output_contract_ids=outputs,
        allowed_tools=capability.allowed_tools,
        effect_scope=capability.effect_scope,
        independent_of_capability_ids=independent_of,
    )


def build_artifact_production_manifest(
    *,
    family: CaseFamilyManifest,
    domain_pack: EvidenceDomainPack,
    evidence_capability: EvidenceFamilyCapability,
    plan: ArtifactPlan,
    projection: RendererArtifactProjection,
    persona_state: PersonaStateSnapshot,
    registry: CapabilityRegistry,
) -> ArtifactProductionManifest:
    if family.readiness != "active_g2" or domain_pack.readiness != "active_g2":
        raise ValueError("domain_pack_not_active_g2")
    if domain_pack.case_family_id != family.family_id:
        raise ValueError("domain_pack_family_mismatch")
    if plan.capability_id not in domain_pack.evidence_capability_ids:
        raise ValueError("domain_pack_capability_not_admitted")
    if plan.capability_id != evidence_capability.capability_id:
        raise ValueError("evidence_capability_mismatch")
    if projection.plan_hash != plan.plan_hash or projection.plan_id != plan.plan_id:
        raise ValueError("detached_renderer_projection")
    if persona_state.state_id != plan.persona_state_id or persona_state.state_hash != plan.persona_state_hash:
        raise ValueError("detached_persona_state")
    expected_projection = build_renderer_projection(
        plan, projection.persona_view, persona_state
    )
    if projection != expected_projection:
        raise ValueError("noncanonical_renderer_projection")
    writer_id = WRITER_BY_FAMILY.get(plan.family_id)
    if writer_id is None:
        raise ValueError(f"unsupported_artifact_family:{plan.family_id}")
    specialists = {item.capability_id: item for item in registry.specialist_capabilities}
    checker_ids = (*COMMON_CHECKERS, VOICE_CHECKER_ID)
    assignments = (
        _assignment(PLANNER_ID, "planner", specialists, plan.plan_hash),
        _assignment(writer_id, "writer", specialists, plan.plan_hash),
        _assignment(RENDERER_ID, "renderer", specialists, plan.plan_hash),
        *(
            _assignment(
                checker_id,
                "checker",
                specialists,
                plan.plan_hash,
                independent_of=(writer_id, RENDERER_ID),
            )
            for checker_id in checker_ids
        ),
    )
    validators = set(domain_pack.required_validator_ids)
    validators.update(evidence_capability.validator_ids)
    validators.update(
        validator
        for assignment in assignments
        for validator in specialists[assignment.specialist_capability_id].validator_ids
    )
    payload = {
        "plan_hash": plan.plan_hash,
        "projection_hash": projection.projection_hash,
        "domain_pack_hash": domain_pack.pack_hash,
        "assignments": tuple(item.assignment_hash for item in assignments),
        "mesh_revision": SPECIALIST_MESH_REVISION,
    }
    return ArtifactProductionManifest(
        manifest_id=f"MESH-MAN-{digest(payload)[:18]}",
        mesh_revision=SPECIALIST_MESH_REVISION,
        world_namespace_commitment=digest(plan.world_namespace),
        matter_namespace_commitment=digest(plan.matter_namespace),
        case_family_id=family.family_id,
        domain_pack_id=domain_pack.pack_id,
        case_family_manifest_hash=family.manifest_hash,
        domain_pack_revision=domain_pack.revision,
        domain_pack_hash=domain_pack.pack_hash,
        evidence_capability_id=evidence_capability.capability_id,
        evidence_capability_revision=evidence_capability.revision,
        artifact_family_id=plan.family_id,
        evidence_capability_contract_hash=digest(evidence_capability),
        channel_kind=plan.channel_kind,
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        renderer_projection_id=projection.projection_id,
        renderer_projection_hash=projection.projection_hash,
        persona_state_id=persona_state.state_id,
        persona_state_hash=persona_state.state_hash,
        persona_view_hash=projection.persona_view.view_hash,
        assertion_scope_commitment=digest(tuple(item.assertion_id for item in projection.allowed_assertions)),
        knowledge_frontier_commitment=plan.knowledge_frontier_hash,
        authority_frontier_commitment=digest(persona_state.authority_ids),
        relationship_scope_commitment=digest(
            {"recipient_ids": plan.recipient_ids, "relationship_ids": projection.persona_view.relationship_ids}
        ),
        lineage_commitment=plan.lineage.lineage_hash,
        required_metadata_commitment=digest(plan.required_metadata_keys),
        simulated_target_native_format=plan.simulated_target_native_format,
        assignments=assignments,
        required_validator_ids=tuple(sorted(validators)),
        excluded_input_planes=EXCLUDED_INPUT_PLANES,
    )


def issue_artifact_mesh_local_receipt(
    manifest: ArtifactProductionManifest,
    staged: StagedArtifact,
    shape_receipt: LocalArtifactShapeReceipt,
) -> ArtifactMeshLocalReceipt:
    if staged.plan_hash != manifest.plan_hash:
        raise ValueError("mesh_staged_plan_mismatch")
    if staged.renderer_projection_hash != manifest.renderer_projection_hash:
        raise ValueError("mesh_staged_projection_mismatch")
    if shape_receipt.plan_hash != manifest.plan_hash:
        raise ValueError("mesh_shape_receipt_plan_mismatch")
    payload = {
        "manifest_hash": manifest.manifest_hash,
        "staged_artifact_hash": digest(staged),
        "shape_receipt_hash": shape_receipt.receipt_hash,
        "decision": "local_mesh_contract_validated_only",
        "mesh_revision": SPECIALIST_MESH_REVISION,
    }
    return ArtifactMeshLocalReceipt(
        receipt_id=f"MESH-LOCAL-{digest(payload)[:18]}",
        mesh_revision=SPECIALIST_MESH_REVISION,
        manifest_id=manifest.manifest_id,
        manifest_hash=manifest.manifest_hash,
        plan_hash=manifest.plan_hash,
        renderer_projection_hash=manifest.renderer_projection_hash,
        staged_artifact_hash=digest(staged),
        local_shape_receipt_hash=shape_receipt.receipt_hash,
        decision="local_mesh_contract_validated_only",
    )


def validate_artifact_mesh(
    *,
    family: CaseFamilyManifest,
    registry: CapabilityRegistry,
    plans: Sequence[ArtifactPlan],
    projections: Sequence[RendererArtifactProjection],
    states: Sequence[PersonaStateSnapshot],
    staged_artifacts: Sequence[StagedArtifact],
    shape_receipts: Sequence[LocalArtifactShapeReceipt],
    manifests: Sequence[ArtifactProductionManifest],
    mesh_receipts: Sequence[ArtifactMeshLocalReceipt],
) -> ArtifactMeshValidationReport:
    findings: list[ArtifactMeshValidationFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(ArtifactMeshValidationFinding(code, subject, message))

    sequences = (plans, projections, staged_artifacts, shape_receipts, manifests, mesh_receipts)
    if len({len(items) for items in sequences}) != 1:
        add("MESH-001", family.family_id, "artifact mesh cardinality mismatch")
    if family.readiness != "active_g2":
        add("MESH-002", family.family_id, "design-only family cannot activate a specialist mesh")
    domain_pack = build_domain_pack(family, registry)
    if domain_pack.readiness != "active_g2":
        add("MESH-003", domain_pack.pack_id, "domain pack is not active G2")
    evidence_by_id = {item.capability_id: item for item in registry.evidence_capabilities}
    projection_by_plan = {item.plan_id: item for item in projections}
    state_by_id = {item.state_id: item for item in states}
    staged_by_plan = {item.plan_id: item for item in staged_artifacts}
    shape_by_plan_hash = {item.plan_hash: item for item in shape_receipts}
    manifest_by_plan = {item.plan_id: item for item in manifests}
    receipt_by_manifest = {item.manifest_id: item for item in mesh_receipts}
    if len(manifest_by_plan) != len(manifests):
        add("MESH-004", family.family_id, "duplicate manifest plan binding")
    if len(receipt_by_manifest) != len(mesh_receipts):
        add("MESH-005", family.family_id, "duplicate mesh receipt binding")
    for plan in plans:
        projection = projection_by_plan.get(plan.plan_id)
        state = state_by_id.get(plan.persona_state_id)
        staged = staged_by_plan.get(plan.plan_id)
        shape = shape_by_plan_hash.get(plan.plan_hash)
        manifest = manifest_by_plan.get(plan.plan_id)
        if None in (projection, state, staged, shape, manifest):
            add("MESH-006", plan.plan_id, "mesh dependency missing")
            continue
        capability = evidence_by_id.get(plan.capability_id)
        if capability is None:
            add("MESH-007", plan.plan_id, "evidence capability missing")
            continue
        try:
            expected_manifest = build_artifact_production_manifest(
                family=family,
                domain_pack=domain_pack,
                evidence_capability=capability,
                plan=plan,
                projection=projection,  # type: ignore[arg-type]
                persona_state=state,  # type: ignore[arg-type]
                registry=registry,
            )
        except ValueError as error:
            add("MESH-008", plan.plan_id, str(error))
            continue
        if manifest != expected_manifest:
            add("MESH-009", plan.plan_id, "manifest is stale, detached, or overbroad")
            continue
        phases = Counter(item.phase for item in manifest.assignments)
        if phases != Counter({"planner": 1, "writer": 1, "renderer": 1, "checker": 4}):
            add("MESH-010", manifest.manifest_id, "assignment phase coverage mismatch")
        writer_ids = {item.specialist_capability_id for item in manifest.assignments if item.phase == "writer"}
        checker_ids = {item.specialist_capability_id for item in manifest.assignments if item.phase == "checker"}
        if writer_ids & checker_ids:
            add("MESH-011", manifest.manifest_id, "writer cannot self-check")
        receipt = receipt_by_manifest.get(manifest.manifest_id)
        if receipt is None:
            add("MESH-012", manifest.manifest_id, "mesh receipt missing")
            continue
        try:
            expected_receipt = issue_artifact_mesh_local_receipt(
                manifest,
                staged,  # type: ignore[arg-type]
                shape,  # type: ignore[arg-type]
            )
        except ValueError as error:
            add("MESH-013", manifest.manifest_id, str(error))
            continue
        if receipt != expected_receipt:
            add("MESH-014", receipt.receipt_id, "mesh receipt is stale or overclaims")
    mesh_commitment = digest(
        {
            "manifests": tuple(item.manifest_hash for item in manifests),
            "receipts": tuple(item.receipt_hash for item in mesh_receipts),
            "revision": SPECIALIST_MESH_REVISION,
        }
    )
    return ArtifactMeshValidationReport(
        passed=not findings,
        findings=tuple(findings),
        mesh_commitment=mesh_commitment,
    )
