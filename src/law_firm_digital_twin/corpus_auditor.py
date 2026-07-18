from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable, Literal

from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
)
from .hashio import digest
from .persona_channel_renderer import (
    QualifiedPersonaChannelRenderBundle,
    validate_persona_channel_bundle,
    validate_persona_channel_batch,
)


CORPUS_AUDITOR_REVISION = "corpus-sameness-continuity-g2-v1"


@dataclass(frozen=True)
class CorpusAuditPolicy:
    policy_id: str = "corpus-audit-policy-g2-v1"
    minimum_group_size: int = 5
    minimum_variants_per_group: int = 2
    concentration_warning_threshold: float = 0.85
    exact_duplicate_limit: int = 1
    synthetic_only: Literal[True] = True

    @property
    def policy_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class CorpusAuditArtifact:
    artifact_commitment: str
    matter_commitment: str
    projection_hash: str
    bundle_hash: str
    logical_artifact_commitment: str
    version_id: str
    claimed_content_hash: str
    revision: int
    parent_version_id: str | None
    parent_content_hash: str | None
    channel_kind: str
    family_id: str
    author_commitment: str
    role_id: str
    voice_signature: str
    variant_id: str
    plan_hash: str
    candidate_hash: str
    body_hash: str
    structure_fingerprint: str
    assertion_trace_hash: str
    rendered_media_type: str
    synthetic_only: bool


@dataclass(frozen=True)
class CorpusAuditFinding:
    code: str
    severity: Literal["error", "warning", "info"]
    subject_commitment: str
    message: str


@dataclass(frozen=True)
class ChannelAuditMetrics:
    channel_kind: str
    artifact_count: int
    unique_body_count: int
    unique_structure_count: int
    unique_variant_count: int
    unique_voice_signature_count: int
    largest_exact_duplicate_group: int
    largest_structure_share: float


@dataclass(frozen=True)
class CorpusAuditReport:
    report_id: str
    passed: bool
    policy_hash: str
    artifact_count: int
    unique_body_count: int
    unique_candidate_count: int
    channel_metrics: tuple[ChannelAuditMetrics, ...]
    findings: tuple[CorpusAuditFinding, ...]
    input_commitment: str
    auditor_revision: str = CORPUS_AUDITOR_REVISION
    synthetic_only: Literal[True] = True
    bodies_included: Literal[False] = False

    @property
    def report_hash(self) -> str:
        return digest(self)

    def public_summary(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "passed": self.passed,
            "policy_hash": self.policy_hash,
            "artifact_count": self.artifact_count,
            "unique_body_count": self.unique_body_count,
            "unique_candidate_count": self.unique_candidate_count,
            "channel_metrics": [asdict(item) for item in self.channel_metrics],
            "finding_counts": dict(
                sorted(Counter(item.severity for item in self.findings).items())
            ),
            "finding_codes": tuple(
                sorted(set(item.code for item in self.findings))
            ),
            "input_commitment": self.input_commitment,
            "auditor_revision": self.auditor_revision,
            "synthetic_only": True,
            "bodies_included": False,
            "scope_statement": (
                "Deterministic G2 sameness and continuity audit; not a legal, "
                "native-fidelity, factual-authority, or prediction validation."
            ),
        }


def _build_corpus_audit_artifact_after_qualification(
    compilation: CaseCompilation,
    bundle: QualifiedPersonaChannelRenderBundle,
) -> CorpusAuditArtifact:
    projection = compilation.renderer_projections[bundle.projection_index]
    structure = tuple(
        (
            segment.section_id,
            segment.function,
            len(segment.assertion_ids),
            segment.style_operation_ids,
        )
        for segment in bundle.candidate.segments
    )
    assertion_trace = tuple(
        assertion_id
        for segment in bundle.candidate.segments
        for assertion_id in segment.assertion_ids
    )
    payload = {
        "matter": digest(
            {
                "world": projection.world_namespace,
                "matter": projection.matter_namespace,
            }
        ),
        "projection_hash": projection.projection_hash,
        "bundle_hash": bundle.qualified_bundle_hash,
        "logical_artifact": digest(
            {
                "world": projection.world_namespace,
                "matter": projection.matter_namespace,
                "logical": projection.lineage.logical_artifact_id,
            }
        ),
        "version_id": projection.lineage.version_id,
        "claimed_content_hash": bundle.staged_artifact.claimed_content_hash,
        "revision": projection.lineage.revision,
        "parent_version_id": projection.lineage.parent_version_id,
        "parent_content_hash": projection.lineage.parent_content_hash,
        "channel_kind": projection.channel_kind,
        "family_id": projection.family_id,
        "author": digest(
            {
                "world": projection.world_namespace,
                "matter": projection.matter_namespace,
                "author": projection.author_id,
            }
        ),
        "role_id": projection.persona_view.role_id,
        "voice_signature": bundle.disposition.voice_signature,
        "variant_id": bundle.plan.variant_id,
        "plan_hash": bundle.plan.plan_hash,
        "candidate_hash": bundle.candidate.candidate_hash,
        "body_hash": digest(bundle.candidate.body),
        "structure_fingerprint": digest(structure),
        "assertion_trace_hash": digest(assertion_trace),
        "rendered_media_type": bundle.candidate.rendered_media_type,
        "synthetic_only": bundle.candidate.synthetic_only,
    }
    return CorpusAuditArtifact(
        artifact_commitment=f"CAUDIT-{digest(payload)[:18]}",
        matter_commitment=payload.pop("matter"),
        author_commitment=payload.pop("author"),
        logical_artifact_commitment=payload.pop("logical_artifact"),
        **payload,
    )


def build_corpus_audit_artifact(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    bundle: QualifiedPersonaChannelRenderBundle,
) -> CorpusAuditArtifact:
    errors = validate_persona_channel_bundle(
        compilation,
        qualification_receipt,
        bundle,
    )
    if errors:
        raise ValueError(
            "invalid_qualified_persona_channel_bundle:" + ",".join(errors)
        )
    return _build_corpus_audit_artifact_after_qualification(
        compilation,
        bundle,
    )


def build_corpus_audit_artifacts(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    bundles: Iterable[QualifiedPersonaChannelRenderBundle],
) -> tuple[CorpusAuditArtifact, ...]:
    bundles_tuple = tuple(bundles)
    errors = validate_persona_channel_batch(
        compilation,
        qualification_receipt,
        bundles_tuple,
    )
    if errors:
        raise ValueError(
            "invalid_qualified_persona_channel_batch:" + ",".join(errors)
        )
    return tuple(
        _build_corpus_audit_artifact_after_qualification(
            compilation,
            bundle,
        )
        for bundle in bundles_tuple
    )



def _largest_group(counter: Counter[str]) -> int:
    return max(counter.values(), default=0)


def audit_persona_channel_corpus(
    artifacts: Iterable[CorpusAuditArtifact],
    policy: CorpusAuditPolicy | None = None,
) -> CorpusAuditReport:
    policy = policy or CorpusAuditPolicy()
    rows = tuple(artifacts)
    findings: list[CorpusAuditFinding] = []

    def add(
        code: str,
        severity: Literal["error", "warning", "info"],
        subject: object,
        message: str,
    ) -> None:
        findings.append(
            CorpusAuditFinding(
                code=code,
                severity=severity,
                subject_commitment=digest(subject),
                message=message,
            )
        )

    commitments = [item.artifact_commitment for item in rows]
    if len(commitments) != len(set(commitments)):
        add(
            "duplicate_audit_input",
            "error",
            commitments,
            "the same audit artifact was supplied more than once",
        )
    identity_keys = [
        (
            item.matter_commitment,
            item.logical_artifact_commitment,
            item.version_id,
        )
        for item in rows
    ]
    if len(identity_keys) != len(set(identity_keys)):
        add(
            "duplicate_lineage_identity",
            "error",
            identity_keys,
            "logical artifact version identity is duplicated",
        )
    for item in rows:
        if not item.synthetic_only:
            add(
                "synthetic_boundary_missing",
                "error",
                item.artifact_commitment,
                "corpus item is not marked synthetic",
            )
        if item.rendered_media_type != "text/plain":
            add(
                "rendered_media_type_mismatch",
                "error",
                item.artifact_commitment,
                "G2 corpus item is not text/plain",
            )

    grouped: dict[str, list[CorpusAuditArtifact]] = defaultdict(list)
    for item in rows:
        grouped[item.channel_kind].append(item)
    metrics: list[ChannelAuditMetrics] = []
    for channel_kind, group in sorted(grouped.items()):
        bodies = Counter(item.body_hash for item in group)
        structures = Counter(item.structure_fingerprint for item in group)
        variants = Counter(item.variant_id for item in group)
        voices = Counter(item.voice_signature for item in group)
        largest_duplicate = _largest_group(bodies)
        largest_structure = _largest_group(structures)
        structure_share = largest_structure / len(group)
        metrics.append(
            ChannelAuditMetrics(
                channel_kind=channel_kind,
                artifact_count=len(group),
                unique_body_count=len(bodies),
                unique_structure_count=len(structures),
                unique_variant_count=len(variants),
                unique_voice_signature_count=len(voices),
                largest_exact_duplicate_group=largest_duplicate,
                largest_structure_share=round(structure_share, 6),
            )
        )
        if largest_duplicate > policy.exact_duplicate_limit:
            add(
                "exact_body_clone",
                "error",
                (channel_kind, tuple(sorted(bodies.items()))),
                "a channel contains an impermissible exact-body clone group",
            )
        if (
            len(group) >= policy.minimum_group_size
            and len(variants) < policy.minimum_variants_per_group
        ):
            add(
                "variant_collapse",
                "error",
                (channel_kind, tuple(sorted(variants.items()))),
                "a sufficiently large channel group lacks deterministic variation",
            )
        if (
            len(group) >= policy.minimum_group_size
            and structure_share >= policy.concentration_warning_threshold
        ):
            add(
                "structure_concentration",
                "warning",
                (channel_kind, tuple(sorted(structures.items()))),
                "channel geometry is highly concentrated; deepen templates before G3",
            )
        if len(group) >= policy.minimum_group_size and len(voices) == 1:
            add(
                "voice_signature_concentration",
                "warning",
                (channel_kind, tuple(sorted(voices.items()))),
                "the current G2 population has one voice signature in this channel",
            )

    by_logical: dict[
        tuple[str, str],
        list[CorpusAuditArtifact],
    ] = defaultdict(list)
    for item in rows:
        by_logical[
            (item.matter_commitment, item.logical_artifact_commitment)
        ].append(item)
    for key, versions in by_logical.items():
        ordered = sorted(versions, key=lambda item: item.revision)
        revisions = [item.revision for item in ordered]
        if revisions != list(range(1, len(ordered) + 1)):
            add(
                "lineage_revision_gap",
                "error",
                key,
                "artifact revision sequence is not contiguous from one",
            )
        for parent, child in zip(ordered, ordered[1:]):
            if child.parent_version_id != parent.version_id:
                add(
                    "lineage_parent_version_mismatch",
                    "error",
                    child.artifact_commitment,
                    "child does not name the preceding version",
                )
            if child.parent_content_hash != parent.claimed_content_hash:
                add(
                    "lineage_parent_content_hash_mismatch",
                    "error",
                    child.artifact_commitment,
                    "child does not bind the preceding content commitment",
                )


    input_commitment = digest(tuple(sorted(rows, key=lambda item: item.artifact_commitment)))
    payload = {
        "passed": not any(item.severity == "error" for item in findings),
        "policy_hash": policy.policy_hash,
        "artifact_count": len(rows),
        "unique_body_count": len({item.body_hash for item in rows}),
        "unique_candidate_count": len({item.candidate_hash for item in rows}),
        "channel_metrics": tuple(metrics),
        "findings": tuple(findings),
        "input_commitment": input_commitment,
        "auditor_revision": CORPUS_AUDITOR_REVISION,
        "synthetic_only": True,
        "bodies_included": False,
    }
    return CorpusAuditReport(
        report_id=f"CORPUS-AUDIT-{digest(payload)[:18]}",
        **payload,
    )

