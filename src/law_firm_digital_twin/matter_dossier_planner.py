from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
    validate_case_qualification_receipt,
)
from .employment_lifecycle_catalog import build_employment_lifecycle_document_catalog
from .hashio import digest
from .litigation_lifecycle_contracts import (
    DossierDocumentNode,
    EmploymentLifecycleDocumentCatalog,
    PublicDossierCatalogSummary,
    QualifiedMatterDossierBlueprint,
)


@dataclass(frozen=True)
class QualifiedDossierSummaryInput:
    compilation: CaseCompilation
    qualification_receipt: CaseCompilationQualificationReceipt
    blueprint: QualifiedMatterDossierBlueprint


PUBLIC_SUMMARY_MINIMUM_BLUEPRINTS = 5


def _build_nodes(
    catalog: EmploymentLifecycleDocumentCatalog,
    operating_projection_hash: str,
) -> tuple[DossierDocumentNode, ...]:
    node_id_by_type = {
        item.document_type_id: (
            f"DNODE-{digest({'catalog': catalog.catalog_hash, 'operating': operating_projection_hash, 'document_type': item.document_type_id})[:18]}"
        )
        for item in catalog.document_types
    }
    return tuple(
        DossierDocumentNode(
            node_id=node_id_by_type[item.document_type_id],
            public_document_type_id=item.document_type_id,
            stage_id=item.stage_id,
            branch_scope=item.branch_scope,
            activation_state=(
                "planning_only"
                if item.branch_scope == "universal"
                else "inactive_pending_kernel_event"
            ),
            prerequisite_node_ids=tuple(
                node_id_by_type[dependency]
                for dependency in item.prerequisite_type_ids
            ),
            activation_event_ids=item.activation_event_ids,
            responsible_role_ids=item.responsible_role_ids,
            confidentiality_class=item.confidentiality_class,
            filing_intent=item.filing_intent,
            billing_task_category=item.billing_task_category,
        )
        for item in catalog.document_types
    )


def build_qualified_matter_dossier_blueprint(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    catalog: EmploymentLifecycleDocumentCatalog | None = None,
) -> QualifiedMatterDossierBlueprint:
    catalog = catalog or build_employment_lifecycle_document_catalog()
    if not validate_case_qualification_receipt(qualification_receipt, compilation):
        raise ValueError("case_qualification_receipt_invalid")
    if compilation.operating.case_family_id != "employment_defense_g2":
        raise ValueError("dossier_family_not_active_employment_g2")
    from .litigation_lifecycle_validator import validate_lifecycle_catalog

    catalog_report = validate_lifecycle_catalog(catalog)
    if not catalog_report.passed:
        raise ValueError("lifecycle_catalog_invalid")
    nodes = _build_nodes(catalog, compilation.operating.projection_hash)
    graph_hash = digest(
        {
            "nodes": nodes,
            "catalog_hash": catalog.catalog_hash,
            "operating_projection_hash": compilation.operating.projection_hash,
        }
    )
    payload = {
        "case_family_id": "employment_defense_g2",
        "operating_projection_hash": compilation.operating.projection_hash,
        "qualification_receipt_hash": qualification_receipt.receipt_hash,
        "catalog_hash": catalog.catalog_hash,
        "graph_hash": graph_hash,
        "revision": catalog.revision,
        "surface": "qualified_nonrendering_operating_dossier",
    }
    return QualifiedMatterDossierBlueprint(
        blueprint_id=f"DOSSIER-{digest(payload)[:18]}",
        case_family_id="employment_defense_g2",
        operating_projection_hash=compilation.operating.projection_hash,
        qualification_receipt_hash=qualification_receipt.receipt_hash,
        catalog_hash=catalog.catalog_hash,
        graph_hash=graph_hash,
        nodes=nodes,
        rule_admission_state="no_rules_admitted",
        source_admission_state="no_sources_admitted",
        branch_activation_authority="future_kernel_event_adapter_required",
        future_branches_active=False,
        legal_compliance_claimed=False,
        native_fidelity_claimed=False,
        canonical_admission=False,
        bodies_included=False,
        runtime_execution=False,
    )


def build_public_dossier_catalog_summary(
    qualified_inputs: tuple[QualifiedDossierSummaryInput, ...],
    catalog: EmploymentLifecycleDocumentCatalog | None = None,
) -> PublicDossierCatalogSummary:
    catalog = catalog or build_employment_lifecycle_document_catalog()
    if len(qualified_inputs) < PUBLIC_SUMMARY_MINIMUM_BLUEPRINTS:
        raise ValueError("public_summary_small_cell_forbidden")
    blueprints = tuple(item.blueprint for item in qualified_inputs)
    if len({item.blueprint_id for item in blueprints}) != len(blueprints):
        raise ValueError("public_summary_duplicate_blueprint")
    for item in qualified_inputs:
        expected = build_qualified_matter_dossier_blueprint(
            item.compilation,
            item.qualification_receipt,
            catalog,
        )
        if item.blueprint != expected:
            raise ValueError("public_summary_unqualified_blueprint")
    if any(item.catalog_hash != catalog.catalog_hash for item in blueprints):
        raise ValueError("public_summary_catalog_mismatch")
    branch_counts = Counter(item.branch_scope for item in catalog.document_types)
    confidentiality_counts = Counter(
        item.confidentiality_class for item in catalog.document_types
    )
    billing_counts = Counter(item.billing_task_category for item in catalog.document_types)
    aggregate_commitment = digest(
        {
            "catalog_hash": catalog.catalog_hash,
            "count": len(qualified_inputs),
            "surface": "public_nonjoinable_catalog_and_count_only",
        }
    )
    return PublicDossierCatalogSummary(
        release_id=f"DOSSIER-PUBLIC-{digest({'catalog': catalog.catalog_hash, 'aggregate': aggregate_commitment})[:18]}",
        case_family_id="employment_defense_g2",
        lifecycle_stage_count=len(catalog.stages),
        document_type_count=len(catalog.document_types),
        branch_scope_counts=tuple(sorted(branch_counts.items())),
        confidentiality_class_counts=tuple(sorted(confidentiality_counts.items())),
        billing_task_category_counts=tuple(sorted(billing_counts.items())),
        planning_blueprint_count=len(qualified_inputs),
        catalog_hash=catalog.catalog_hash,
        aggregate_blueprint_commitment=aggregate_commitment,
        source_admission_state="no_sources_admitted",
        legal_compliance_claimed=False,
        native_fidelity_claimed=False,
        runtime_execution=False,
    )

