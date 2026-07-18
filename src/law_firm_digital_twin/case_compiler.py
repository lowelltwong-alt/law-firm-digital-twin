from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal, Sequence

from .case_manifest import (
    CapabilityRegistry,
    CaseDesignBlueprint,
    SealedDesignLabel,
    build_capability_registry,
    build_population_blueprints,
)
from .evidence_contracts import (
    ArtifactPlan,
    FactAssertion,
    RendererArtifactProjection,
    StagedArtifact,
    LocalArtifactShapeReceipt,
    build_artifact_plan,
    build_renderer_projection,
    issue_local_shape_receipt,
    render_deterministic_g2_fixture,
    validate_staged_artifact,
    validate_local_shape_receipt,
    validate_lineage_graph,
    validate_plan_authority,
)
from .hashio import canonical_json, digest
from .models import RulePack
from .persona_state import (
    PersonaStateSnapshot,
    RendererPersonaView,
    compile_persona_snapshot,
    project_persona_for_renderer,
    validate_persona_snapshot,
)
from .specialist_mesh import (
    build_artifact_production_manifest,
    build_domain_pack,
    issue_artifact_mesh_local_receipt,
    validate_artifact_mesh,
)
from .specialist_mesh_contracts import (
    ArtifactMeshLocalReceipt,
    ArtifactProductionManifest,
)
from .world import build_personas


CASE_COMPILER_REVISION = "case-compiler-g2-v1"
PROJECTION_SCHEMA_REVISION = "projection-contract-g2-v1"
FORBIDDEN_OPERATING_FIELDS = (
    "seed",
    "sealed_axis_labels",
    "design_labels",
    "target_posture",
    "target_strength",
    "declared_conflict",
    "conflict_purpose",
    "resolution_track",
    "representation_quality",
    "procedural_quality",
    "evaluator_case_id",
    "evaluation_projection",
    "oracle",
    "world_truth",
)


@dataclass(frozen=True)
class CompileRequest:
    blueprint: CaseDesignBlueprint
    registry: CapabilityRegistry
    rule_pack: RulePack
    compiler_revision: str = CASE_COMPILER_REVISION


@dataclass(frozen=True)
class CompiledFact:
    claim_id: str
    fact_id: str
    value: str
    occurs_day: int
    domain: str
    known_by: tuple[tuple[str, int], ...]

    @property
    def fact_commitment(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SealedConflictSpec:
    conflict_id: str
    issue_fact_id: str
    claim_ids: tuple[str, ...]
    purpose: str

    @property
    def conflict_commitment(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class SealedCaseState:
    sealed_case_id: str
    world_namespace: str
    matter_namespace: str
    case_family_id: str
    source_blueprint_commitment: str
    axis_labels: tuple[tuple[str, str], ...]
    design_labels: tuple[SealedDesignLabel, ...]
    target_posture: str
    resolution_track: str
    procedural_quality: str
    representation_quality: str
    facts: tuple[CompiledFact, ...]
    conflicts: tuple[SealedConflictSpec, ...]
    rule_pack_commitment: str
    compiler_revision: str
    schema_revision: str = PROJECTION_SCHEMA_REVISION

    @property
    def sealed_state_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class OperatingActorFrontier:
    frontier_id: str
    actor_id: str
    role_id: str
    organization: str
    as_of_day: int
    known_fact_count: int
    authority_count: int


@dataclass(frozen=True)
class OperatingArtifactSummary:
    public_plan_id: str
    capability_id: str
    family_id: str
    created_day: int
    author_role_id: str
    simulated_target_native_format: str
    initial: bool
    synthetic_only: bool = True


@dataclass(frozen=True)
class OperatingCaseProjection:
    projection_id: str
    case_family_id: str
    jurisdiction_label: str
    rule_pack_id: str
    compiler_revision: str
    schema_revision: str
    synthetic_only: bool
    non_predictive: bool
    initial_artifacts: tuple[OperatingArtifactSummary, ...]
    actor_frontiers: tuple[OperatingActorFrontier, ...]
    planned_artifact_count: int

    @property
    def projection_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class EvaluationCaseProjection:
    evaluator_case_id: str
    case_family_id: str
    axis_labels: tuple[tuple[str, str], ...]
    design_labels: tuple[SealedDesignLabel, ...]
    conflict_specs: tuple[SealedConflictSpec, ...]
    fact_commitments: tuple[str, ...]
    scoring_rubric_revision: str
    compiler_revision: str
    synthetic_only: bool = True
    real_world_prediction: bool = False

    @property
    def projection_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CaseCompilation:
    compilation_id: str
    compiler_revision: str
    schema_revision: str
    source_blueprint: CaseDesignBlueprint
    source_blueprint_commitment: str
    presentation_scope_commitment: str
    sealed: SealedCaseState
    operating: OperatingCaseProjection
    evaluation: EvaluationCaseProjection
    persona_states: tuple[PersonaStateSnapshot, ...]
    renderer_views: tuple[RendererPersonaView, ...]
    artifact_plans: tuple[ArtifactPlan, ...]
    renderer_projections: tuple[RendererArtifactProjection, ...]
    staged_artifacts: tuple[StagedArtifact, ...]
    local_shape_receipts: tuple[LocalArtifactShapeReceipt, ...]
    artifact_production_manifests: tuple[ArtifactProductionManifest, ...]
    artifact_mesh_receipts: tuple[ArtifactMeshLocalReceipt, ...]

    @property
    def compilation_hash(self) -> str:
        return digest(self)

    def operating_export(self) -> dict[str, Any]:
        return asdict(self.operating)

    def evaluation_export(self) -> dict[str, Any]:
        return asdict(self.evaluation)


@dataclass(frozen=True)
class CompilationFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class CompilationValidationReport:
    passed: bool
    findings: tuple[CompilationFinding, ...]
    compilation_hash: str
    validator_revision: str = CASE_COMPILER_REVISION





@dataclass(frozen=True)
class CaseCompilationQualificationReceipt:
    receipt_id: str
    compilation_id: str
    compilation_hash: str
    validator_revision: str
    sealed_authority_validated: Literal[True]
    lineage_graph_validated: Literal[True]
    local_shape_receipts_validated: Literal[True]
    specialist_mesh_validated: Literal[True]
    canonical_admission: Literal[False] = False

    @property
    def receipt_hash(self) -> str:
        return digest(self)


def _claim(
    fact_id: str,
    value: str,
    occurs_day: int,
    domain: str,
    *known_by: tuple[str, int],
) -> CompiledFact:
    return CompiledFact(
        claim_id=f"CLAIM-{digest({'fact': fact_id, 'value': value, 'day': occurs_day, 'known': known_by})[:18]}",
        fact_id=fact_id,
        value=value,
        occurs_day=occurs_day,
        domain=domain,
        known_by=tuple(sorted(known_by)),
    )


def _build_fact_design(
    axis: dict[str, str],
) -> tuple[tuple[CompiledFact, ...], tuple[SealedConflictSpec, ...]]:
    merits = axis["merits_posture"]
    evidence_shape = axis["evidence_shape"]
    merits_values = {
        "defense_favorable": (
            "four_exceptions_verified_with_prior_coaching",
            "documented_operational_exception_after_hr_consult",
        ),
        "claimant_favorable": (
            "mixed_exceptions_with_disputed_entries",
            "manager_acted_before_required_hr_consult",
        ),
        "balanced": (
            "two_excused_one_disputed_one_unverified",
            "consultation_started_but_final_sequence_is_disputed",
        ),
        "deeply_ambiguous": (
            "source_records_incomplete_and_partly_corrupted",
            "sequence_cannot_be_resolved_from_available_records",
        ),
    }
    status_values = {
        "directional_defense": (
            "recommendation_pending_on_day_38",
            "review_in_progress_on_day_40",
        ),
        "directional_claimant": (
            "decision_final_on_day_38",
            "manager_had_communicated_final_intent_by_day_40",
        ),
        "mixed_conflicting": (
            "decision_final_on_day_38",
            "no_final_recommendation_received_by_day_40",
        ),
        "sparse_or_corrupted": (
            "decision_language_appears_final_but_source_is_partial",
            "hr_record_fragment_does_not_resolve_finality",
        ),
        "noisy_redundant": (
            "decision_language_mixed_with_staffing_discussion",
            "review_request_remained_open_on_day_40",
        ),
    }
    attendance, policy_alignment = merits_values[merits]
    manager_status, hr_status = status_values[evidence_shape]
    common = (
        ("responsible_lawyer", 50),
        ("litigation_paralegal", 50),
        ("independent_expert", 100),
    )
    facts = (
        _claim("referral_summary", "synthetic_adverse_employment_referral", 0, "employment_action", ("intake_coordinator", 0), ("claim_handler", 0), *common),
        _claim("policy_process", "consult_hr_before_discharge_with_documented_exception", 1, "policy", ("hr_witness", 1), ("manager_witness", 1), *common),
        _claim("protected_activity", "employee_reported_wage_and_safety_concerns", 25, "protected_activity", ("hr_witness", 25), ("manager_witness", 27), *common),
        _claim("attendance_support", attendance, 35, "attendance", ("billing_specialist", 35), ("hr_witness", 35), ("manager_witness", 35), *common),
        _claim("hr_review_scheduled", "day_39_review_tentative", 37, "employment_action", ("manager_witness", 37), ("hr_witness", 37), *common),
        _claim("decision_status", manager_status, 38, "employment_action", ("manager_witness", 38), *common),
        _claim("decision_status", hr_status, 40, "employment_action", ("hr_witness", 40), *common),
        _claim("termination_day", "44", 44, "employment_action", ("manager_witness", 44), ("hr_witness", 44), *common),
        _claim("stated_reason", "attendance_and_performance", 44, "employment_action", ("manager_witness", 44), ("hr_witness", 44), *common),
        _claim("policy_alignment", policy_alignment, 44, "policy", ("manager_witness", 44), ("hr_witness", 44), *common),
        _claim("procedural_posture", axis["procedural_quality"], 52, "procedure", ("responsible_lawyer", 52), ("litigation_paralegal", 52)),
    )
    decision_claims = tuple(item for item in facts if item.fact_id == "decision_status")
    conflicts: tuple[SealedConflictSpec, ...] = ()
    if len({item.value for item in decision_claims}) > 1:
        conflicts = (
            SealedConflictSpec(
                conflict_id=f"CONFLICT-{digest(tuple(item.claim_id for item in decision_claims))[:18]}",
                issue_fact_id="decision_status",
                claim_ids=tuple(item.claim_id for item in decision_claims),
                purpose="test independent detection of incompatible contemporaneous decision-timing accounts",
            ),
        )
    return facts, conflicts


def _knowledge_for_actor(
    facts: Iterable[CompiledFact],
    actor_id: str,
    as_of_day: int,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                fact.fact_id
                for fact in facts
                for known_actor, learned_day in fact.known_by
                if known_actor == actor_id and learned_day <= as_of_day
            }
        )
    )


def _assertions_for(
    facts: Iterable[CompiledFact],
    world_namespace: str,
    matter_namespace: str,
    actor_id: str,
    as_of_day: int,
    fact_ids: Iterable[str],
) -> tuple[FactAssertion, ...]:
    assertions: list[FactAssertion] = []
    used_claims: set[str] = set()
    for fact_id in fact_ids:
        candidates = [
            fact
            for fact in facts
            if fact.fact_id == fact_id
            and fact.claim_id not in used_claims
            and any(
                known_actor == actor_id and learned_day <= as_of_day
                for known_actor, learned_day in fact.known_by
            )
        ]
        if not candidates:
            raise ValueError(
                f"knowledge_frontier_violation:{actor_id}:{fact_id}:{as_of_day}"
            )
        fact = sorted(candidates, key=lambda item: (item.occurs_day, item.claim_id))[0]
        used_claims.add(fact.claim_id)
        learned_day = min(
            day
            for known_actor, day in fact.known_by
            if known_actor == actor_id and day <= as_of_day
        )
        assertions.append(
            FactAssertion(
                world_namespace=world_namespace,
                matter_namespace=matter_namespace,
                author_id=actor_id,
                fact_id=fact.fact_id,
                value=fact.value,
                source_kind="sealed_synthetic_claim",
                source_id=fact.claim_id,
                learned_day=learned_day,
            )
        )
    return tuple(assertions)


def _plan_specs(axis: dict[str, str]) -> tuple[dict[str, Any], ...]:
    sparse = axis["evidence_shape"] == "sparse_or_corrupted"
    noisy = axis["evidence_shape"] == "noisy_redundant"

    def spec(
        family: str,
        logical: str,
        author: str,
        recipients: tuple[str, ...],
        day: int,
        facts: tuple[str, ...],
        *,
        initial: bool = False,
        responsive: bool = True,
        missing: bool = False,
        native_format: str = "application/json",
    ) -> dict[str, Any]:
        availability = (
            "initial"
            if initial
            else "missing_or_corrupted"
            if missing
            else "discoverable"
            if responsive or noisy
            else "withheld_nonresponsive"
        )
        return {
            "family": family,
            "logical": logical,
            "author": author,
            "recipients": recipients,
            "day": day,
            "facts": facts,
            "availability": availability,
            "responsive": responsive,
            "format": native_format,
        }

    return (
        spec("employment_litigation", "referral", "intake_coordinator", ("responsible_lawyer",), 0, ("referral_summary",), initial=True),
        spec("employment_policy", "discipline-policy", "hr_witness", ("manager_witness",), 1, ("policy_process",), initial=True),
        spec("employment_payroll", "attendance-summary", "billing_specialist", (), 35, ("attendance_support",), missing=sparse, native_format="text/csv"),
        spec("employment_noise", "benefits-reminder", "hr_witness", (), 36, (), responsive=False),
        spec("employment_calendar", "manager-calendar", "manager_witness", ("hr_witness",), 37, ("hr_review_scheduled",), missing=sparse),
        spec("employment_email", "manager-decision-email", "manager_witness", ("hr_witness",), 38, ("decision_status",)),
        spec("employment_email", "hr-followup-email", "hr_witness", ("manager_witness",), 40, ("decision_status",), missing=sparse),
        spec("employment_hr_record", "termination-record", "manager_witness", (), 44, ("termination_day", "stated_reason", "policy_alignment"), initial=True),
        spec("employment_expert", "workplace-practices-analysis", "independent_expert", ("responsible_lawyer",), 120, ("attendance_support", "decision_status", "decision_status", "policy_alignment")),
    )





def _build_operating_projection(
    *,
    case_family_id: str,
    rule_pack: RulePack,
    persona_states: tuple[PersonaStateSnapshot, ...],
    plans: tuple[ArtifactPlan, ...],
    profiles: dict[str, Any],
    compiler_revision: str,
) -> OperatingCaseProjection:
    latest_by_actor: dict[str, PersonaStateSnapshot] = {}
    for state in persona_states:
        current = latest_by_actor.get(state.actor_id)
        if current is None or (state.as_of_day, state.revision) > (
            current.as_of_day,
            current.revision,
        ):
            latest_by_actor[state.actor_id] = state
    frontiers = tuple(
        OperatingActorFrontier(
            frontier_id=f"FRONTIER-{digest({'world': state.world_namespace, 'actor': state.actor_id, 'day': state.as_of_day, 'surface': 'operating'})[:18]}",
            actor_id=state.actor_id,
            role_id=state.role_id,
            organization=state.organization,
            as_of_day=state.as_of_day,
            known_fact_count=len(state.knowledge_fact_ids),
            authority_count=len(state.authority_ids),
        )
        for state in sorted(latest_by_actor.values(), key=lambda item: item.actor_id)
    )
    initial = tuple(
        OperatingArtifactSummary(
            public_plan_id=f"OPLAN-{digest({'logical': plan.lineage.logical_artifact_id, 'surface': 'operating'})[:18]}",
            capability_id=plan.capability_id,
            family_id=plan.family_id,
            created_day=plan.created_day,
            author_role_id=profiles[plan.author_id].role_id,
            simulated_target_native_format=plan.simulated_target_native_format,
            initial=True,
        )
        for plan in plans
        if plan.availability == "initial"
    )
    payload = {
        "case_family_id": case_family_id,
        "jurisdiction_label": rule_pack.jurisdiction_label,
        "rule_pack_id": rule_pack.rule_pack_id,
        "compiler_revision": compiler_revision,
        "schema_revision": PROJECTION_SCHEMA_REVISION,
        "synthetic_only": True,
        "non_predictive": True,
        "initial_artifacts": initial,
        "actor_frontiers": frontiers,
        "planned_artifact_count": len(plans),
    }
    return OperatingCaseProjection(
        projection_id=f"OPROJ-{digest(payload)[:18]}",
        **payload,
    )


def _build_evaluation_projection(
    blueprint: CaseDesignBlueprint,
    conflicts: tuple[SealedConflictSpec, ...],
    facts: tuple[CompiledFact, ...],
    compiler_revision: str,
) -> EvaluationCaseProjection:
    payload = {
        "case_family_id": blueprint.case_family_id,
        "axis_labels": blueprint.sealed_axis_labels,
        "design_labels": blueprint.design_labels,
        "conflict_specs": conflicts,
        "fact_commitments": tuple(item.fact_commitment for item in facts),
        "scoring_rubric_revision": "synthetic-case-design-recovery-g2-v1",
        "compiler_revision": compiler_revision,
        "synthetic_only": True,
        "real_world_prediction": False,
    }
    return EvaluationCaseProjection(
        evaluator_case_id=f"EVAL-{digest({'blueprint': blueprint.sealed_commitment_hash, 'surface': 'evaluation'})[:18]}",
        **payload,
    )


def _validate_request(request: CompileRequest) -> tuple[Any, dict[str, str]]:
    families = {item.family_id: item for item in request.registry.case_families}
    family = families.get(request.blueprint.case_family_id)
    if family is None:
        raise ValueError("unknown_case_family")
    if family.readiness != "active_g2":
        raise ValueError("case_family_not_active")
    if not family.synthetic_only or family.fidelity_level != "G2":
        raise ValueError("family_boundary_invalid")
    axes = {item.axis_id: item for item in request.registry.population_axes}
    selected = dict(request.blueprint.sealed_axis_labels)
    if set(selected) != set(axes):
        raise ValueError("population_axis_set_mismatch")
    for axis_id, bucket_id in selected.items():
        if bucket_id not in {item.bucket_id for item in axes[axis_id].buckets}:
            raise ValueError(f"unknown_population_bucket:{axis_id}:{bucket_id}")
    return family, selected



def _presentation_scope_commitment(
    blueprint: CaseDesignBlueprint,
    compiler_revision: str,
) -> str:
    return digest(
        {
            "design_id": blueprint.design_id,
            "ordinal": blueprint.ordinal,
            "case_family_id": blueprint.case_family_id,
            "compiler_revision": compiler_revision,
            "policy": "presentation-scope-safe-inputs-g2-v1",
        }
    )



def compile_case_design(request: CompileRequest) -> CaseCompilation:
    family, selected = _validate_request(request)
    blueprint_hash = request.blueprint.sealed_commitment_hash
    presentation_scope_commitment = _presentation_scope_commitment(
        request.blueprint, request.compiler_revision
    )
    world_namespace = f"WNS-{digest({'blueprint': blueprint_hash, 'surface': 'world'})[:18]}"
    matter_namespace = f"MNS-{digest({'blueprint': blueprint_hash, 'surface': 'matter'})[:18]}"
    facts, conflicts = _build_fact_design(selected)
    profiles = build_personas()
    capabilities = {
        item.family_id: item
        for item in request.registry.evidence_capabilities
        if item.readiness == "active_g2"
    }

    states: list[PersonaStateSnapshot] = []
    domain_pack = build_domain_pack(family, request.registry)
    views: list[RendererPersonaView] = []
    plans: list[ArtifactPlan] = []
    renderer_projections: list[RendererArtifactProjection] = []
    staged: list[StagedArtifact] = []
    receipts: list[LocalArtifactShapeReceipt] = []
    production_manifests: list[ArtifactProductionManifest] = []
    mesh_receipts: list[ArtifactMeshLocalReceipt] = []

    for spec in _plan_specs(selected):
        capability = capabilities.get(spec["family"])
        if capability is None:
            raise ValueError(f"missing_evidence_capability:{spec['family']}")
        author_id = spec["author"]
        profile = profiles[author_id]
        known = _knowledge_for_actor(facts, author_id, spec["day"])
        assertions = _assertions_for(
            facts,
            world_namespace,
            matter_namespace,
            author_id,
            spec["day"],
            spec["facts"],
        )
        relationship_ids = tuple(
            f"REL-{digest({'world': world_namespace, 'source': author_id, 'target': target})[:16]}"
            for target in spec["recipients"]
        )
        state = compile_persona_snapshot(
            profile,
            world_namespace=world_namespace,
            matter_namespace=matter_namespace,
            as_of_day=spec["day"],
            knowledge_fact_ids=known,
            knowledge_assertion_ids=(item.assertion_id for item in assertions),
            authority_ids=profile.initial_authority,
            relationship_ids=relationship_ids,
        )
        view = project_persona_for_renderer(
            state,
            allowed_fact_ids=(item.fact_id for item in assertions),
            allowed_assertion_ids=(item.assertion_id for item in assertions),
        )
        plan = build_artifact_plan(
            world_namespace=world_namespace,
            matter_namespace=matter_namespace,
            capability=capability,
            author_id=author_id,
            recipient_ids=spec["recipients"],
            created_day=spec["day"],
            allowed_assertions=assertions,
            persona_state=state,
            logical_artifact_id=(
                f"ART-{digest({'world': world_namespace, 'logical': spec['logical']})[:18]}"
            ),
            responsive=spec["responsive"],
            privileged=False,
            availability=spec["availability"],
            simulated_target_native_format=spec["format"],
            purpose=f"{spec['family']}:{spec['logical']}",
        )
        renderer_projection = build_renderer_projection(plan, view, state)
        staged_artifact = render_deterministic_g2_fixture(renderer_projection)
        receipt = issue_local_shape_receipt(staged_artifact, renderer_projection)
        states.append(state)
        views.append(view)
        plans.append(plan)
        production_manifest = build_artifact_production_manifest(
            family=family,
            domain_pack=domain_pack,
            evidence_capability=capability,
            plan=plan,
            projection=renderer_projection,
            persona_state=state,
            registry=request.registry,
        )
        mesh_receipt = issue_artifact_mesh_local_receipt(
            production_manifest,
            staged_artifact,
            receipt,
        )
        production_manifests.append(production_manifest)
        mesh_receipts.append(mesh_receipt)
        renderer_projections.append(renderer_projection)
        staged.append(staged_artifact)
        receipts.append(receipt)

    plans_tuple = tuple(plans)
    required_capabilities = {
        f"evidence.{item}.v1" for item in family.required_evidence_capabilities
    }
    observed_capabilities = {item.capability_id for item in plans_tuple}
    if not required_capabilities.issubset(observed_capabilities):
        raise ValueError("required_evidence_capability_missing")
    if len(plans_tuple) > family.max_artifacts:
        raise ValueError("matter_artifact_capacity_exceeded")

    operating = _build_operating_projection(
        case_family_id=family.family_id,
        rule_pack=request.rule_pack,
        persona_states=tuple(states),
        plans=plans_tuple,
        profiles=profiles,
        compiler_revision=request.compiler_revision,
    )
    evaluation = _build_evaluation_projection(
        request.blueprint,
        conflicts,
        facts,
        request.compiler_revision,
    )
    sealed_payload = {
        "world_namespace": world_namespace,
        "matter_namespace": matter_namespace,
        "case_family_id": family.family_id,
        "source_blueprint_commitment": blueprint_hash,
        "axis_labels": request.blueprint.sealed_axis_labels,
        "design_labels": request.blueprint.design_labels,
        "target_posture": selected["merits_posture"],
        "resolution_track": selected["resolution_track"],
        "procedural_quality": selected["procedural_quality"],
        "representation_quality": selected["representation_quality"],
        "facts": facts,
        "conflicts": conflicts,
        "rule_pack_commitment": digest(request.rule_pack),
        "compiler_revision": request.compiler_revision,
        "schema_revision": PROJECTION_SCHEMA_REVISION,
    }
    sealed = SealedCaseState(
        sealed_case_id=f"SEALED-{digest(sealed_payload)[:18]}",
        **sealed_payload,
    )
    compilation_payload = {
        "blueprint": blueprint_hash,
        "sealed": sealed.sealed_state_hash,
        "operating": operating.projection_hash,
        "evaluation": evaluation.projection_hash,
        "plans": tuple(item.plan_hash for item in plans_tuple),
        "persona_states": tuple(item.state_hash for item in states),
        "renderers": tuple(item.projection_hash for item in renderer_projections),
        "staged": tuple(digest(item) for item in staged),
        "receipts": tuple(item.receipt_hash for item in receipts),
        "compiler_revision": request.compiler_revision,
        "presentation_scope_commitment": presentation_scope_commitment,
        "specialist_manifests": tuple(item.manifest_hash for item in production_manifests),
        "specialist_mesh_receipts": tuple(item.receipt_hash for item in mesh_receipts),
    }
    compilation = CaseCompilation(
        compilation_id=f"COMPILE-{digest(compilation_payload)[:18]}",
        compiler_revision=request.compiler_revision,
        source_blueprint=request.blueprint,
        schema_revision=PROJECTION_SCHEMA_REVISION,
        source_blueprint_commitment=blueprint_hash,
        presentation_scope_commitment=presentation_scope_commitment,
        sealed=sealed,
        operating=operating,
        evaluation=evaluation,
        persona_states=tuple(states),
        renderer_views=tuple(views),
        artifact_plans=plans_tuple,
        renderer_projections=tuple(renderer_projections),
        staged_artifacts=tuple(staged),
        local_shape_receipts=tuple(receipts),
        artifact_production_manifests=tuple(production_manifests),
        artifact_mesh_receipts=tuple(mesh_receipts),
    )
    report = validate_case_compilation(compilation, request.registry)
    if not report.passed:



        raise ValueError(";".join(item.code for item in report.findings))
    return compilation


def _sealed_assertion_grant_ids(sealed: SealedCaseState) -> frozenset[str]:
    grants: set[str] = set()
    for fact in sealed.facts:
        for actor_id, learned_day in fact.known_by:
            grants.add(
                FactAssertion(
                    world_namespace=sealed.world_namespace,
                    matter_namespace=sealed.matter_namespace,
                    author_id=actor_id,
                    fact_id=fact.fact_id,
                    value=fact.value,
                    source_kind="sealed_synthetic_claim",
                    source_id=fact.claim_id,
                    learned_day=learned_day,
                ).assertion_id
            )
    return frozenset(grants)






def validate_case_compilation(
    compilation: CaseCompilation,
    registry: CapabilityRegistry | None = None,
) -> CompilationValidationReport:
    registry = registry or build_capability_registry()
    findings: list[CompilationFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(CompilationFinding(code, subject, message))

    families = {item.family_id: item for item in registry.case_families}
    family = families.get(compilation.sealed.case_family_id)
    if family is None:
        add("CMP-001", "case_family", "unknown case family")
    elif family.readiness != "active_g2":
        add("CMP-002", family.family_id, "case family is not active G2")
    if (
        compilation.source_blueprint_commitment
        != compilation.sealed.source_blueprint_commitment
    ):
        add("CMP-003", compilation.compilation_id, "blueprint commitment mismatch")
    if compilation.compiler_revision != compilation.sealed.compiler_revision:
        add("CMP-004", compilation.compilation_id, "compiler revision mismatch")
    if compilation.schema_revision != PROJECTION_SCHEMA_REVISION:
        add("CMP-005", compilation.compilation_id, "projection schema mismatch")
    if compilation.operating.case_family_id != compilation.sealed.case_family_id:
        add("CMP-028", compilation.compilation_id, "operating case family mismatch")
    if compilation.evaluation.case_family_id != compilation.sealed.case_family_id:
        add("CMP-029", compilation.compilation_id, "evaluation case family mismatch")
    if compilation.operating.compiler_revision != compilation.compiler_revision:
        add("CMP-030", compilation.compilation_id, "operating compiler revision mismatch")

    operating_text = canonical_json(compilation.operating).lower()
    for term in FORBIDDEN_OPERATING_FIELDS:
        if term in operating_text:
            add(
                "CMP-006",
                compilation.operating.projection_id,
                f"forbidden operating field: {term}",
            )
    for _, value in compilation.sealed.axis_labels:
        if f'"{value.lower()}"' in operating_text:
            add("CMP-007", compilation.operating.projection_id, "axis value leaked")
    if compilation.evaluation.evaluator_case_id.lower() in operating_text:
        add("CMP-008", compilation.operating.projection_id, "evaluation join leaked")
    if (
        not compilation.evaluation.synthetic_only
        or compilation.evaluation.real_world_prediction
    ):
        add("CMP-009", compilation.evaluation.evaluator_case_id, "evaluation boundary invalid")

    plan_ids = [item.plan_id for item in compilation.artifact_plans]
    staged_ids = [item.staged_artifact_id for item in compilation.staged_artifacts]
    renderer_plan_ids = [item.plan_id for item in compilation.renderer_projections]
    receipt_ids = [item.receipt_id for item in compilation.local_shape_receipts]
    receipt_plan_hashes = [item.plan_hash for item in compilation.local_shape_receipts]
    view_ids = [item.view_id for item in compilation.renderer_views]
    if len(plan_ids) != len(set(plan_ids)):
        add("CMP-011", compilation.compilation_id, "duplicate plan id")
    if len(staged_ids) != len(set(staged_ids)):
        add("CMP-012", compilation.compilation_id, "duplicate staged id")
    if len(renderer_plan_ids) != len(set(renderer_plan_ids)):
        add("CMP-031", compilation.compilation_id, "duplicate renderer plan id")
    if len(receipt_ids) != len(set(receipt_ids)):
        add("CMP-032", compilation.compilation_id, "duplicate receipt id")
    if len(receipt_plan_hashes) != len(set(receipt_plan_hashes)):
        add("CMP-033", compilation.compilation_id, "duplicate receipt plan hash")
    if len(view_ids) != len(set(view_ids)):
        add("CMP-034", compilation.compilation_id, "duplicate renderer view id")
    if not (
        len(compilation.artifact_plans)
        == len(compilation.renderer_projections)
        == len(compilation.staged_artifacts)
        == len(compilation.local_shape_receipts)
        == len(compilation.artifact_production_manifests)
        == len(compilation.artifact_mesh_receipts)
    ):
        add("CMP-013", compilation.compilation_id, "pipeline cardinality mismatch")
    for lineage_error in validate_lineage_graph(
        compilation.artifact_plans,
        compilation.staged_artifacts,
    ):
        add("CMP-LINEAGE", compilation.compilation_id, lineage_error)

    capabilities = {item.capability_id: item for item in registry.evidence_capabilities}
    renderer_by_plan = {
        item.plan_id: item for item in compilation.renderer_projections
    }
    staged_by_plan = {item.plan_id: item for item in compilation.staged_artifacts}
    receipt_by_plan = {
        item.plan_hash: item for item in compilation.local_shape_receipts
    }
    state_by_id = {item.state_id: item for item in compilation.persona_states}
    view_by_id = {item.view_id: item for item in compilation.renderer_views}
    sealed_grants = _sealed_assertion_grant_ids(compilation.sealed)
    for plan in compilation.artifact_plans:
        capability = capabilities.get(plan.capability_id)
        if capability is None or capability.readiness != "active_g2":
            add("CMP-014", plan.plan_id, "inactive evidence capability")
        elif plan.capability_revision != capability.revision:
            add("CMP-035", plan.plan_id, "stale evidence capability revision")
        if any(item.assertion_id not in sealed_grants for item in plan.allowed_assertions):
            add("CMP-036", plan.plan_id, "assertion is not grounded in sealed fact authority")
        if plan.world_namespace != compilation.sealed.world_namespace:
            add("CMP-015", plan.plan_id, "cross-world plan")
        if plan.matter_namespace != compilation.sealed.matter_namespace:
            add("CMP-016", plan.plan_id, "cross-matter plan")
        state = state_by_id.get(plan.persona_state_id)
        if state is None or state.state_hash != plan.persona_state_hash:
            add("CMP-017", plan.plan_id, "missing or stale persona state")
        elif not validate_persona_snapshot(state).passed:
            add("CMP-018", plan.plan_id, "invalid persona state")
        elif state.matter_namespace != compilation.sealed.matter_namespace:
            add("CMP-037", plan.plan_id, "cross-matter persona state")
        elif any(item.assertion_id not in state.knowledge_assertion_ids for item in plan.allowed_assertions):
            add("CMP-038", plan.plan_id, "plan assertion not granted to persona state")
        if state is not None and capability is not None:
            for authority_error in validate_plan_authority(plan, state, capability):
                add("CMP-AUTHORITY", plan.plan_id, authority_error)
        renderer = renderer_by_plan.get(plan.plan_id)
        staged = staged_by_plan.get(plan.plan_id)
        if renderer is None or renderer.plan_hash != plan.plan_hash:
            add("CMP-019", plan.plan_id, "renderer projection missing or stale")
            continue
        if renderer.world_namespace != compilation.sealed.world_namespace:
            add("CMP-020", plan.plan_id, "cross-world renderer")
        if renderer.matter_namespace != compilation.sealed.matter_namespace:
            add("CMP-039", plan.plan_id, "cross-matter renderer")
        if renderer.capability_revision != plan.capability_revision:
            add("CMP-040", plan.plan_id, "renderer capability revision mismatch")
        trusted_view = view_by_id.get(renderer.persona_view.view_id)
        if trusted_view != renderer.persona_view:
            add("CMP-041", plan.plan_id, "renderer persona view is missing or stale")
        elif state is None or renderer.persona_view.persona_state_hash != state.state_hash:
            add("CMP-042", plan.plan_id, "renderer persona state commitment mismatch")
        elif state is not None:
            expected_view = project_persona_for_renderer(
                state,
                allowed_fact_ids=(item.fact_id for item in plan.allowed_assertions),
                allowed_assertion_ids=(item.assertion_id for item in plan.allowed_assertions),
            )
            if renderer.persona_view != expected_view:
                add("CMP-043", plan.plan_id, "renderer persona view is not derived from trusted state")
            else:
                expected_renderer = build_renderer_projection(
                    plan,
                    expected_view,
                    state,
                )
                if renderer != expected_renderer:
                    add("CMP-048", plan.plan_id, "renderer projection is not canonical for plan")
        if staged is None:
            add("CMP-021", plan.plan_id, "staged artifact missing")
            continue
        artifact_report = validate_staged_artifact(staged, renderer)
        for item in artifact_report.findings:
            add(f"CMP-ART-{item.code}", item.subject, item.message)
        receipt = receipt_by_plan.get(plan.plan_hash)
        if receipt is None:
            add("CMP-022", plan.plan_id, "candidate receipt missing")
        elif receipt.canonical_admission is not False:
            add("CMP-023", plan.plan_id, "worker claimed canonical admission")
        elif staged is not None:
            for receipt_error in validate_local_shape_receipt(receipt, staged, renderer):
                add("CMP-RECEIPT", receipt.receipt_id, receipt_error)

    if family is not None:
        required = {
            f"evidence.{item}.v1" for item in family.required_evidence_capabilities
        }
        observed = {item.capability_id for item in compilation.artifact_plans}
        if not required.issubset(observed):
            add("CMP-024", family.family_id, "required evidence capability missing")
        counts = Counter(item.capability_id for item in compilation.artifact_plans)
        for capability_id, count in counts.items():
            capability = capabilities.get(capability_id)
            if capability is not None and count > capability.max_per_matter:
                add("CMP-025", capability_id, "capability limit exceeded")
        if len(compilation.artifact_plans) > family.max_artifacts:
            add("CMP-026", family.family_id, "matter artifact limit exceeded")
        mesh_report = validate_artifact_mesh(
            family=family,
            registry=registry,
            plans=compilation.artifact_plans,
            projections=compilation.renderer_projections,
            states=compilation.persona_states,
            staged_artifacts=compilation.staged_artifacts,
            shape_receipts=compilation.local_shape_receipts,
            manifests=compilation.artifact_production_manifests,
            mesh_receipts=compilation.artifact_mesh_receipts,
        )
        for item in mesh_report.findings:
            add(f"CMP-{item.code}", item.subject, item.message)

    compilation_payload = {
        "blueprint": compilation.source_blueprint_commitment,
        "sealed": compilation.sealed.sealed_state_hash,
        "operating": compilation.operating.projection_hash,
        "evaluation": compilation.evaluation.projection_hash,
        "plans": tuple(item.plan_hash for item in compilation.artifact_plans),
        "persona_states": tuple(item.state_hash for item in compilation.persona_states),
        "renderers": tuple(item.projection_hash for item in compilation.renderer_projections),
        "staged": tuple(digest(item) for item in compilation.staged_artifacts),
        "receipts": tuple(item.receipt_hash for item in compilation.local_shape_receipts),
        "compiler_revision": compilation.compiler_revision,
        "presentation_scope_commitment": compilation.presentation_scope_commitment,
        "specialist_manifests": tuple(item.manifest_hash for item in compilation.artifact_production_manifests),
        "specialist_mesh_receipts": tuple(item.receipt_hash for item in compilation.artifact_mesh_receipts),
    }
    if (
        compilation.source_blueprint.sealed_commitment_hash
        != compilation.source_blueprint_commitment
    ):
        add("CMP-045", compilation.compilation_id, "source blueprint commitment mismatch")
    expected_presentation_scope = _presentation_scope_commitment(
        compilation.source_blueprint,
        compilation.compiler_revision,
    )
    if compilation.presentation_scope_commitment != expected_presentation_scope:
        add("CMP-046", compilation.compilation_id, "presentation scope derivation mismatch")
    if len(compilation.presentation_scope_commitment) != 64:
        add("CMP-044", compilation.compilation_id, "presentation scope commitment invalid")
    expected_id = f"COMPILE-{digest(compilation_payload)[:18]}"
    if compilation.compilation_id != expected_id:
        add("CMP-027", compilation.compilation_id, "compilation mismatch")
    return CompilationValidationReport(
        passed=not findings,
        findings=tuple(findings),
        compilation_hash=compilation.compilation_hash,
    )



def qualify_case_compilation(
    compilation: CaseCompilation,
    registry: CapabilityRegistry | None = None,
) -> CaseCompilationQualificationReceipt:
    report = validate_case_compilation(compilation, registry)
    if not report.passed:
        raise ValueError("case_compilation_validation_failed")
    payload = {
        "compilation_id": compilation.compilation_id,
        "compilation_hash": report.compilation_hash,
        "validator_revision": report.validator_revision,
        "sealed_authority_validated": True,
        "lineage_graph_validated": True,
        "local_shape_receipts_validated": True,
        "specialist_mesh_validated": True,
    }
    return CaseCompilationQualificationReceipt(
        receipt_id=f"CASEQUAL-{digest(payload)[:18]}",
        canonical_admission=False,
        **payload,
    )


def validate_case_qualification_receipt(
    receipt: CaseCompilationQualificationReceipt,
    compilation: CaseCompilation,
    registry: CapabilityRegistry | None = None,
) -> bool:
    try:
        return receipt == qualify_case_compilation(compilation, registry)
    except ValueError:
        return False





def compile_population_fixture(
    *,
    seed: str,
    count: int,
    rule_pack: RulePack,
    registry: CapabilityRegistry | None = None,
) -> tuple[CaseCompilation, ...]:
    registry = registry or build_capability_registry()
    blueprints = build_population_blueprints(seed, count)
    return tuple(
        compile_case_design(
            CompileRequest(
                blueprint=blueprint,
                registry=registry,
                rule_pack=rule_pack,
            )
        )
        for blueprint in blueprints
    )


def build_public_corpus_manifest(
    compilations: Sequence[CaseCompilation],
) -> dict[str, Any]:
    if not compilations:
        raise ValueError("corpus_cannot_be_empty")
    registry = build_capability_registry()
    allowed_public_families = {
        item.family_id
        for item in registry.case_families
        if item.readiness == "active_g2" and item.synthetic_only
    }
    for compilation in compilations:
        if not validate_case_compilation(compilation, registry).passed:
            raise ValueError("invalid_compilation_for_public_manifest")
        if compilation.operating.case_family_id not in allowed_public_families:
            raise ValueError("public_case_family_not_allowlisted")
    families = sorted({item.operating.case_family_id for item in compilations})
    capability_counts = Counter(
        plan.capability_id
        for compilation in compilations
        for plan in compilation.artifact_plans
    )
    cases = [
        {
            "public_case_id": (
                f"PUBLIC-{digest({'compilation': item.compilation_id, 'surface': 'public'})[:18]}"
            ),
            "case_family_id": item.operating.case_family_id,
            "artifact_count": len(item.artifact_plans),
            "initial_artifact_count": len(item.operating.initial_artifacts),
            "synthetic_only": True,
        }
        for item in compilations
    ]
    manifest = {
        "schema_version": "public-corpus-manifest-g2-v1",
        "compiler_revision": CASE_COMPILER_REVISION,
        "synthetic_only": True,
        "non_predictive": True,
        "jurisdiction_compliance": False,
        "case_count": len(compilations),
        "case_families": families,
        "capability_counts": dict(sorted(capability_counts.items())),
        "cases": cases,
        "prohibited_uses": [
            "real_world_prediction",
            "legal_or_medical_advice",
            "jurisdiction_compliance",
            "identity_reconstruction",
        ],
    }
    text = canonical_json(manifest).lower()
    forbidden = (
        *FORBIDDEN_OPERATING_FIELDS,
        "source_blueprint_commitment",
        "fact_commitment",
        "conflict_spec",
        "persona_state",
        "renderer_projection",
        "protected_activity",
    )
    if any(term in text for term in forbidden):
        raise ValueError("public_manifest_leakage")
    return manifest




def build_public_blueprint_receipts(
    blueprints: Sequence[CaseDesignBlueprint],
) -> dict[str, Any]:
    if not blueprints:
        raise ValueError("blueprint_receipts_cannot_be_empty")
    records = [
        {
            "public_blueprint_id": (
                f"PUBLIC-BP-{digest({'blueprint': item.sealed_commitment_hash, 'surface': 'public'})[:18]}"
            ),
            "case_family_id": item.case_family_id,
            "sealed_design_commitment": item.sealed_commitment_hash,
            "synthetic_only": True,
        }
        for item in blueprints
    ]
    result = {
        "schema_version": "public-blueprint-receipts-g2-v1",
        "synthetic_only": True,
        "commitment_is_not_access_control": True,
        "case_count": len(records),
        "records": records,
        "excluded_fields": [
            "seed",
            "sealed_axis_labels",
            "design_labels",
            "evaluation_join_keys",
        ],
    }
    text = canonical_json(result).lower()
    if any(
        term in text
        for term in (
            "merits_posture",
            "evidence_shape",
            "procedural_quality",
            "representation_quality",
            "resolution_track",
            "target_posture",
            "conflict_purpose",
        )
    ):
        raise ValueError("public_blueprint_receipt_leakage")
    return result

