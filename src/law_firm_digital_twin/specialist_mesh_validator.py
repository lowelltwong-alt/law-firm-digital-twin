from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal, Sequence

from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
    validate_case_qualification_receipt,
)
from .case_manifest import build_capability_registry
from .hashio import digest
from .specialist_mesh import build_domain_pack, validate_artifact_mesh
from .specialist_mesh_contracts import SPECIALIST_MESH_REVISION


@dataclass(frozen=True)
class QualifiedSpecialistMeshInput:
    compilation: CaseCompilation
    qualification_receipt: CaseCompilationQualificationReceipt


@dataclass(frozen=True)
class SpecialistMeshCorpusReport:
    report_id: str
    input_commitment: str
    case_count: int
    artifact_count: int
    domain_pack_count: int
    evidence_capability_counts: tuple[tuple[str, int], ...]
    writer_capability_counts: tuple[tuple[str, int], ...]
    checker_capability_counts: tuple[tuple[str, int], ...]
    assignment_phase_counts: tuple[tuple[str, int], ...]
    local_contract_receipt_count: int
    runtime_specialist_execution_count: Literal[0]
    qualified_binding_rate: Literal[1.0]
    evaluator_revision: str = SPECIALIST_MESH_REVISION
    synthetic_only: Literal[True] = True
    factual_authority_claimed: Literal[False] = False
    canonical_admission_claimed: Literal[False] = False
    artifact_bodies_included: Literal[False] = False

    @property
    def report_hash(self) -> str:
        return digest(self)

    def public_summary(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "case_count": self.case_count,
            "artifact_count": self.artifact_count,
            "domain_pack_count": self.domain_pack_count,
            "evidence_capability_counts": dict(self.evidence_capability_counts),
            "writer_capability_counts": dict(self.writer_capability_counts),
            "checker_capability_counts": dict(self.checker_capability_counts),
            "assignment_phase_counts": dict(self.assignment_phase_counts),
            "local_contract_receipt_count": self.local_contract_receipt_count,
            "runtime_specialist_execution_count": 0,
            "qualified_binding_rate": 1.0,
            "mesh_revision": self.evaluator_revision,
            "synthetic_only": True,
            "factual_authority_claimed": False,
            "canonical_admission_claimed": False,
            "artifact_bodies_included": False,
            "scope_statement": (
                "Aggregate G2 specialist ownership and least-privilege contract coverage only; "
                "no runtime AI specialist execution, legal conclusion, or canonical admission is claimed."
            ),
        }


def evaluate_specialist_mesh_corpus(
    inputs: Sequence[QualifiedSpecialistMeshInput],
) -> SpecialistMeshCorpusReport:
    if not inputs:
        raise ValueError("specialist_mesh_corpus_cannot_be_empty")
    registry = build_capability_registry()
    family_by_id = {item.family_id: item for item in registry.case_families}
    evidence_counts: Counter[str] = Counter()
    writer_counts: Counter[str] = Counter()
    checker_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    domain_pack_hashes: set[str] = set()
    seen_compilations: set[str] = set()
    artifact_count = 0
    receipt_count = 0
    input_rows: list[dict[str, str]] = []
    for item in inputs:
        compilation = item.compilation
        if compilation.compilation_id in seen_compilations:
            raise ValueError("duplicate_specialist_mesh_compilation")
        seen_compilations.add(compilation.compilation_id)
        if not validate_case_qualification_receipt(
            item.qualification_receipt,
            compilation,
            registry,
        ):
            raise ValueError("unqualified_specialist_mesh_compilation")
        family = family_by_id.get(compilation.operating.case_family_id)
        if family is None:
            raise ValueError("unknown_specialist_mesh_case_family")
        report = validate_artifact_mesh(
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
        if not report.passed:
            raise ValueError("specialist_mesh_validation_failed")
        domain_pack_hashes.add(build_domain_pack(family, registry).pack_hash)
        artifact_count += len(compilation.artifact_production_manifests)
        receipt_count += len(compilation.artifact_mesh_receipts)
        input_rows.append(
            {
                "compilation_hash": compilation.compilation_hash,
                "qualification_receipt_hash": item.qualification_receipt.receipt_hash,
                "mesh_commitment": report.mesh_commitment,
            }
        )
        for manifest in compilation.artifact_production_manifests:
            evidence_counts[manifest.evidence_capability_id] += 1
            for assignment in manifest.assignments:
                phase_counts[assignment.phase] += 1
                if assignment.phase == "writer":
                    writer_counts[assignment.specialist_capability_id] += 1
                elif assignment.phase == "checker":
                    checker_counts[assignment.specialist_capability_id] += 1
                if assignment.runtime_executed:
                    raise ValueError("unqualified_runtime_specialist_execution_claim")
    input_commitment = digest(tuple(input_rows))
    payload = {
        "input_commitment": input_commitment,
        "case_count": len(inputs),
        "artifact_count": artifact_count,
        "domain_pack_hashes": tuple(sorted(domain_pack_hashes)),
        "evidence_counts": tuple(sorted(evidence_counts.items())),
        "writer_counts": tuple(sorted(writer_counts.items())),
        "checker_counts": tuple(sorted(checker_counts.items())),
        "phase_counts": tuple(sorted(phase_counts.items())),
        "receipt_count": receipt_count,
        "revision": SPECIALIST_MESH_REVISION,
    }
    return SpecialistMeshCorpusReport(
        report_id=f"MESH-CORPUS-{digest(payload)[:18]}",
        input_commitment=input_commitment,
        case_count=len(inputs),
        artifact_count=artifact_count,
        domain_pack_count=len(domain_pack_hashes),
        evidence_capability_counts=tuple(sorted(evidence_counts.items())),
        writer_capability_counts=tuple(sorted(writer_counts.items())),
        checker_capability_counts=tuple(sorted(checker_counts.items())),
        assignment_phase_counts=tuple(sorted(phase_counts.items())),
        local_contract_receipt_count=receipt_count,
        runtime_specialist_execution_count=0,
        qualified_binding_rate=1.0,
    )
