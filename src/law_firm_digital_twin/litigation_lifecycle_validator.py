from __future__ import annotations

from collections import Counter, deque
from typing import TYPE_CHECKING

from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
    validate_case_qualification_receipt,
)
from .employment_lifecycle_catalog import build_employment_lifecycle_document_catalog
from .hashio import canonical_json, digest
from .litigation_lifecycle_contracts import (
    DossierValidationFinding,
    DossierValidationReport,
    EmploymentLifecycleDocumentCatalog,
    PublicDossierCatalogSummary,
    QualifiedMatterDossierBlueprint,
)

if TYPE_CHECKING:
    from .matter_dossier_planner import QualifiedDossierSummaryInput


ALLOWED_BRANCH_SCOPES = frozenset(
    {
        "universal",
        "motion",
        "settlement",
        "mediation",
        "administrative_agency_design_only",
        "arbitration_design_only",
        "trial",
        "appeal",
    }
)
ALLOWED_CONFIDENTIALITY_CLASSES = frozenset(
    {
        "internal_work_product",
        "attorney_client_simulated",
        "carrier_confidential_simulated",
        "discovery_confidential_simulated",
        "mediation_confidential_simulated",
        "expert_work_product_simulated",
        "billing_confidential_simulated",
    }
)
ALLOWED_RECORD_KINDS = frozenset(
    {
        "structured_record",
        "correspondence",
        "memorandum",
        "index",
        "log",
        "tabular_record",
        "agreement_surrogate",
        "filing_surrogate",
        "transcript_surrogate",
        "report_surrogate",
        "presentation_surrogate",
    }
)
ALLOWED_ROLES = frozenset(
    {
        "intake",
        "conflicts",
        "lawyer",
        "paralegal",
        "docketing",
        "deadline_reviewer",
        "carrier",
        "billing",
        "witness",
        "expert",
    }
)
ALLOWED_FACT_DOMAINS = frozenset(
    {"employment_action", "policy", "attendance", "protected_activity", "damages"}
)
FORBIDDEN_TEXT = (
    "pacer",
    "court_compliant",
    "court-compliant",
    "legal_compliance_true",
    "native_fidelity_true",
    "real_client",
    "real_person",
    "raw_email",
    "enron",
    "http://",
    "https://",
    "mbti",
    "left brain",
    "right brain",
    "class determines",
    "education determines",
    "profession determines",
    "target_posture",
    "target_strength",
    "resolution_track",
    "resolution_outcome",
    "evaluator_case_id",
    "world_namespace",
    "matter_namespace",
    "oracle",
)
REQUIRED_DOCUMENT_TYPE_IDS = frozenset(
    {
        "referral_packet",
        "conflicts_search_report",
        "matter_opening_checklist",
        "initial_litigation_budget",
        "preservation_notice",
        "fact_chronology",
        "answer_surrogate",
        "independent_deadline_reconciliation",
        "collection_log",
        "responsiveness_privilege_decision_log",
        "production_manifest",
        "deposition_transcript_surrogate",
        "testimony_conflict_update",
        "expert_method_and_limitations_record",
        "expert_independence_counsel_verification",
        "expert_report_surrogate",
        "administrative_agency_position_response_surrogate",
        "motion_surrogate",
        "settlement_authority_record",
        "mediation_statement_surrogate",
        "arbitration_award_surrogate",
        "verdict_and_judgment_surrogate",
        "appellate_decision_surrogate",
        "time_entry",
        "invoice",
        "billing_reduction_record",
        "billing_appeal",
        "billing_appeal_decision",
        "cash_application_record",
        "write_off_record",
        "finance_reconciliation",
        "resolution_transition_record",
        "matter_closure_checklist",
        "archive_integrity_receipt",
    }
)


def _dag_errors(
    ids: tuple[str, ...],
    dependencies: dict[str, tuple[str, ...]],
    expected_root: str,
) -> tuple[str, ...]:
    id_set = set(ids)
    errors: list[str] = []
    indegree = {item: 0 for item in ids}
    outgoing: dict[str, list[str]] = {item: [] for item in ids}
    for item in ids:
        for dependency in dependencies.get(item, ()):
            if dependency not in id_set:
                errors.append(f"unknown_dependency:{item}:{dependency}")
                continue
            if dependency == item:
                errors.append(f"self_dependency:{item}")
                continue
            indegree[item] += 1
            outgoing[dependency].append(item)
    queue = deque(sorted(item for item, count in indegree.items() if count == 0))
    visited: list[str] = []
    while queue:
        item = queue.popleft()
        visited.append(item)
        for target in sorted(outgoing[item]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(visited) != len(ids):
        errors.append("cycle_detected")
    roots = tuple(item for item in ids if not dependencies.get(item, ()))
    if roots != (expected_root,):
        errors.append("root_must_be_referral_packet")
    reachable = set(roots)
    frontier = deque(roots)
    while frontier:
        item = frontier.popleft()
        for target in outgoing.get(item, ()):
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    if reachable != id_set:
        errors.append("unreachable_document_type")
    return tuple(errors)


def validate_lifecycle_catalog(
    catalog: EmploymentLifecycleDocumentCatalog,
) -> DossierValidationReport:
    findings: list[DossierValidationFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(DossierValidationFinding(code, subject, message))

    expected = build_employment_lifecycle_document_catalog()
    if catalog != expected:
        add("DLC-001", catalog.catalog_id, "catalog is not the canonical revision")
    if catalog.case_family_id != "employment_defense_g2":
        add("DLC-002", catalog.catalog_id, "catalog family is not active employment G2")
    if (
        catalog.source_admission_state != "no_sources_admitted"
        or catalog.external_access
        or catalog.runtime_execution
        or catalog.learning_eligible
        or catalog.canonical_truth_write
    ):
        add("DLC-003", catalog.catalog_id, "catalog crossed a G2 authority boundary")
    if catalog.activation_gate != "human_document_family_activation_and_fixture_qualification":
        add("DLC-004", catalog.catalog_id, "catalog activation gate changed")
    stage_ids = tuple(item.stage_id for item in catalog.stages)
    if len(stage_ids) != len(set(stage_ids)):
        add("DLC-005", catalog.catalog_id, "duplicate lifecycle stage")
    if tuple(item.ordinal for item in catalog.stages) != tuple(
        sorted(item.ordinal for item in catalog.stages)
    ):
        add("DLC-006", catalog.catalog_id, "stage order is not deterministic")
    stage_by_id = {item.stage_id: item for item in catalog.stages}
    document_ids = tuple(item.document_type_id for item in catalog.document_types)
    if len(document_ids) != len(set(document_ids)):
        add("DLC-007", catalog.catalog_id, "duplicate document type")
    if not REQUIRED_DOCUMENT_TYPE_IDS.issubset(document_ids):
        add("DLC-008", catalog.catalog_id, "required lifecycle document type missing")
    if set(item.branch_scope for item in catalog.document_types) != ALLOWED_BRANCH_SCOPES:
        add("DLC-009", catalog.catalog_id, "branch coverage is incomplete or unknown")
    for item in catalog.stages:
        if item.branch_scope not in ALLOWED_BRANCH_SCOPES or item.runtime_execution:
            add("DLC-010", item.stage_id, "stage scope or execution boundary invalid")
    for item in catalog.document_types:
        stage = stage_by_id.get(item.stage_id)
        if stage is None or stage.branch_scope != item.branch_scope:
            add("DLC-011", item.document_type_id, "document stage or branch mismatch")
        if item.record_kind not in ALLOWED_RECORD_KINDS or item.target_shape != item.record_kind:
            add("DLC-012", item.document_type_id, "record kind is outside the closed vocabulary")
        if item.confidentiality_class not in ALLOWED_CONFIDENTIALITY_CLASSES:
            add("DLC-013", item.document_type_id, "confidentiality class is unknown")
        if not item.responsible_role_ids or not set(item.responsible_role_ids).issubset(ALLOWED_ROLES):
            add("DLC-014", item.document_type_id, "responsible role is missing or unknown")
        if not set(item.recipient_role_ids).issubset(ALLOWED_ROLES):
            add("DLC-015", item.document_type_id, "recipient role is unknown")
        if not set(item.fact_domain_dependencies).issubset(ALLOWED_FACT_DOMAINS):
            add("DLC-016", item.document_type_id, "fact domain is unknown")
        if (
            item.source_class != "synthetic_design_specification"
            or item.rule_admission_state != "no_rules_admitted"
            or item.body_included
            or item.runtime_execution
            or item.legal_compliance_claimed
            or item.native_fidelity_claimed
        ):
            add("DLC-017", item.document_type_id, "document authority boundary invalid")
        if item.filing_intent not in {"not_a_filing", "simulated_filing_intent_only"}:
            add("DLC-018", item.document_type_id, "filing intent is invalid")
        if not item.activation_event_ids or any(
            not value.startswith("deferred.kernel_adapter_unimplemented.") for value in item.activation_event_ids
        ):
            add("DLC-019", item.document_type_id, "activation is not kernel-event-bound")
        text = canonical_json(item).lower()
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text:
                add("DLC-020", item.document_type_id, f"forbidden content: {forbidden}")
    dependencies = {
        item.document_type_id: item.prerequisite_type_ids
        for item in catalog.document_types
    }
    for graph_error in _dag_errors(document_ids, dependencies, "referral_packet"):
        add("DLC-021", catalog.catalog_id, graph_error)
    return DossierValidationReport(
        passed=not findings,
        findings=tuple(findings),
        subject_hash=catalog.catalog_hash,
    )


def validate_qualified_matter_dossier_blueprint(
    blueprint: QualifiedMatterDossierBlueprint,
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    catalog: EmploymentLifecycleDocumentCatalog | None = None,
) -> DossierValidationReport:
    findings: list[DossierValidationFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(DossierValidationFinding(code, subject, message))

    catalog = catalog or build_employment_lifecycle_document_catalog()
    catalog_report = validate_lifecycle_catalog(catalog)
    for item in catalog_report.findings:
        add(item.code, item.subject, item.message)
    if not validate_case_qualification_receipt(qualification_receipt, compilation):
        add("DLP-001", blueprint.blueprint_id, "case qualification receipt is invalid")
    if compilation.operating.case_family_id != "employment_defense_g2":
        add("DLP-002", blueprint.blueprint_id, "source family is not active employment G2")
    if (
        blueprint.case_family_id != "employment_defense_g2"
        or blueprint.operating_projection_hash != compilation.operating.projection_hash
        or blueprint.qualification_receipt_hash != qualification_receipt.receipt_hash
        or blueprint.catalog_hash != catalog.catalog_hash
    ):
        add("DLP-003", blueprint.blueprint_id, "source binding is stale or cross-case")
    if (
        blueprint.rule_admission_state != "no_rules_admitted"
        or blueprint.source_admission_state != "no_sources_admitted"
        or blueprint.branch_activation_authority != "future_kernel_event_adapter_required"
        or blueprint.future_branches_active
        or blueprint.legal_compliance_claimed
        or blueprint.native_fidelity_claimed
        or blueprint.canonical_admission
        or blueprint.bodies_included
        or blueprint.runtime_execution
    ):
        add("DLP-004", blueprint.blueprint_id, "blueprint crossed a G2 authority boundary")
    node_ids = tuple(item.node_id for item in blueprint.nodes)
    if len(node_ids) != len(set(node_ids)):
        add("DLP-005", blueprint.blueprint_id, "duplicate dossier node")
    if len(blueprint.nodes) != len(catalog.document_types):
        add("DLP-006", blueprint.blueprint_id, "dossier/catalog cardinality mismatch")
    by_type = {item.public_document_type_id: item for item in blueprint.nodes}
    if set(by_type) != {item.document_type_id for item in catalog.document_types}:
        add("DLP-007", blueprint.blueprint_id, "dossier document types do not match catalog")
    for definition in catalog.document_types:
        node = by_type.get(definition.document_type_id)
        if node is None:
            continue
        expected_activation = (
            "planning_only"
            if definition.branch_scope == "universal"
            else "inactive_pending_kernel_event"
        )
        if node.activation_state != expected_activation:
            add("DLP-008", node.node_id, "future branch activation or universal-state tamper")
        if node.branch_scope != definition.branch_scope or node.stage_id != definition.stage_id:
            add("DLP-009", node.node_id, "node stage or branch mismatch")
        if node.activation_event_ids != definition.activation_event_ids:
            add("DLP-010", node.node_id, "node activation event changed")
        if node.body_included or node.runtime_execution:
            add("DLP-011", node.node_id, "node claimed body generation or runtime execution")
    dependencies = {
        item.node_id: item.prerequisite_node_ids for item in blueprint.nodes
    }
    expected_root = by_type.get("referral_packet")
    for graph_error in _dag_errors(
        node_ids,
        dependencies,
        expected_root.node_id if expected_root is not None else "missing_referral_root",
    ):
        add("DLP-012", blueprint.blueprint_id, graph_error)
    expected_graph_hash = digest(
        {
            "nodes": blueprint.nodes,
            "catalog_hash": catalog.catalog_hash,
            "operating_projection_hash": compilation.operating.projection_hash,
        }
    )
    if blueprint.graph_hash != expected_graph_hash:
        add("DLP-013", blueprint.blueprint_id, "graph commitment mismatch")
    text = canonical_json(blueprint).lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in text:
            add("DLP-014", blueprint.blueprint_id, f"forbidden operating content: {forbidden}")
    from .matter_dossier_planner import build_qualified_matter_dossier_blueprint

    try:
        expected = build_qualified_matter_dossier_blueprint(
            compilation,
            qualification_receipt,
            catalog,
        )
    except ValueError:
        expected = None
    if expected is None or blueprint != expected:
        add("DLP-015", blueprint.blueprint_id, "blueprint is not the canonical derivation")
    return DossierValidationReport(
        passed=not findings,
        findings=tuple(findings),
        subject_hash=blueprint.blueprint_hash,
    )


def validate_public_dossier_catalog_summary(
    summary: PublicDossierCatalogSummary,
    qualified_inputs: tuple[QualifiedDossierSummaryInput, ...],
    catalog: EmploymentLifecycleDocumentCatalog | None = None,
) -> DossierValidationReport:
    findings: list[DossierValidationFinding] = []

    def add(code: str, subject: str, message: str) -> None:
        findings.append(DossierValidationFinding(code, subject, message))

    catalog = catalog or build_employment_lifecycle_document_catalog()
    from .matter_dossier_planner import build_public_dossier_catalog_summary

    try:
        expected = build_public_dossier_catalog_summary(qualified_inputs, catalog)
    except ValueError as exc:
        expected = None
        add("DPS-001", summary.release_id, str(exc))
    if expected is None or summary != expected:
        add("DPS-002", summary.release_id, "public summary is not canonical")
    if (
        summary.source_admission_state != "no_sources_admitted"
        or summary.legal_compliance_claimed
        or summary.native_fidelity_claimed
        or summary.runtime_execution
    ):
        add("DPS-003", summary.release_id, "public summary crossed a G2 boundary")
    if summary.planning_blueprint_count < 5:
        add("DPS-004", summary.release_id, "public summary violates the small-cell floor")
    if summary.document_type_count != len(catalog.document_types):
        add("DPS-005", summary.release_id, "public document count mismatch")
    if dict(summary.branch_scope_counts) != Counter(
        item.branch_scope for item in catalog.document_types
    ):
        add("DPS-006", summary.release_id, "public branch counts mismatch")
    text = canonical_json(summary).lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in text:
            add("DPS-007", summary.release_id, f"forbidden public content: {forbidden}")
    return DossierValidationReport(
        passed=not findings,
        findings=tuple(findings),
        subject_hash=digest(summary),
    )
