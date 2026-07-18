from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
from statistics import median
from typing import Iterable, Literal

from .case_compiler import (
    CaseCompilation,
    CaseCompilationQualificationReceipt,
)
from .communication_culture import (
    derive_actor_identity_commitment,
    derive_organization_identity_commitment,
)
from .hashio import digest
from .persona_channel_renderer import (
    QualifiedPersonaChannelRenderBundle,
    validate_persona_channel_batch,
)


CORPUS_DIVERSITY_REVISION = "corpus-diversity-evaluator-g2-v1"
_REALIZED_OPERATION_PREFIXES = ("opening_", "geometry_", "layout_")
_REALIZED_LEGACY_OPERATIONS = frozenset({"lead_with_bottom_line", "chronological_order", "compact_geometry"})


@dataclass(frozen=True)
class CorpusDiversityPolicy:
    policy_id: str = "corpus-diversity-policy-g2-v1"
    minimum_channel_size: int = 10
    minimum_effective_families: int = 3
    maximum_family_share: float = 0.70
    minimum_presentation_ratio: float = 0.20
    near_template_threshold: float = 0.92
    near_template_warning_threshold: float = 0.60
    trivial_variant_warning_threshold: float = 0.60
    cross_author_collapse_threshold: float = 0.15
    cross_author_caricature_threshold: float = 0.80
    public_minimum_cell: int = 5

    @property
    def policy_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class QualifiedCorpusDiversityInput:
    compilation: CaseCompilation
    qualification_receipt: CaseCompilationQualificationReceipt
    bundles: tuple[QualifiedPersonaChannelRenderBundle, ...]


@dataclass(frozen=True)
class CorpusDiversityArtifact:
    artifact_commitment: str
    matter_commitment: str
    author_commitment: str
    organization_commitment: str
    culture_commitment: str
    channel_kind: str
    family_id: str
    role_id: str
    effective_voice_signature: str
    effective_geometry_signature: str
    channel_contract_hash: str
    section_sequence: tuple[str, ...]
    segment_geometry: tuple[tuple[str, str], ...]
    assertion_positions: tuple[int, ...]
    style_operation_ids: tuple[str, ...]
    realized_operation_ids: tuple[str, ...]
    normalized_nonassertive_block_ids: tuple[str, ...]
    audience_mode: str
    channel_compatibility: str
    presentation_fingerprint: str
    semantic_skeleton_tokens: tuple[str, ...]
    variant_id: str
    factual_trace_hash: str
    body_hash: str
    qualified_bundle_hash: str
    source_compilation_hash: str
    synthetic_only: bool


@dataclass(frozen=True)
class DiversityFinding:
    code: str
    severity: Literal["error", "warning", "info"]
    subject_commitment: str
    message: str


@dataclass(frozen=True)
class ChannelDiversityMetrics:
    channel_kind: str
    artifact_count: int
    eligible: bool
    effective_voice_family_count: int
    effective_geometry_family_count: int
    effective_combined_family_count: int
    presentation_family_count: int
    largest_effective_family_share: float
    meaningful_presentation_ratio: float
    trivial_variant_ratio: float
    near_template_pair_rate: float
    cross_author_median_distance: float | None
    cross_author_status: str


@dataclass(frozen=True)
class CorpusDiversityReport:
    report_id: str
    passed: bool
    policy_hash: str
    artifact_count: int
    qualified_binding_rate: float
    factual_trace_coverage: float
    cross_channel_schema_separation: float
    eligible_channel_count: int
    insufficient_channel_count: int
    within_author_eligible_count: int
    within_author_inconsistency_count: int
    organization_eligible_count: int
    organization_inconsistency_count: int
    channel_metrics: tuple[ChannelDiversityMetrics, ...]
    findings: tuple[DiversityFinding, ...]
    input_commitment: str
    evaluator_revision: str = CORPUS_DIVERSITY_REVISION
    synthetic_only: Literal[True] = True
    human_realism_validated: Literal[False] = False
    native_fidelity_validated: Literal[False] = False
    bodies_included: Literal[False] = False

    @property
    def report_hash(self) -> str:
        return digest(self)

    def public_summary(self) -> dict[str, object]:
        public_channels = [
            asdict(item)
            for item in self.channel_metrics
            if item.artifact_count >= 5
        ]
        suppressed = sum(
            1 for item in self.channel_metrics if item.artifact_count < 5
        )
        return {
            "report_id": self.report_id,
            "passed": self.passed,
            "policy_hash": self.policy_hash,
            "artifact_count": self.artifact_count,
            "qualified_binding_rate": round(self.qualified_binding_rate, 2),
            "factual_trace_coverage": round(self.factual_trace_coverage, 2),
            "cross_channel_schema_separation": round(
                self.cross_channel_schema_separation,
                2,
            ),
            "eligible_channel_count": self.eligible_channel_count,
            "insufficient_channel_count": self.insufficient_channel_count,
            "within_author_eligible_count": self.within_author_eligible_count,
            "within_author_inconsistency_count": (
                self.within_author_inconsistency_count
            ),
            "organization_eligible_count": self.organization_eligible_count,
            "organization_inconsistency_count": (
                self.organization_inconsistency_count
            ),
            "suppressed_small_cell_count": suppressed,
            "channel_metrics": public_channels,
            "finding_counts": dict(
                sorted(Counter(item.severity for item in self.findings).items())
            ),
            "finding_codes": tuple(
                sorted(set(item.code for item in self.findings))
            ),
            "input_commitment": self.input_commitment,
            "evaluator_revision": self.evaluator_revision,
            "synthetic_only": True,
            "human_realism_validated": False,
            "native_fidelity_validated": False,
            "bodies_included": False,
            "scope_statement": (
                "Deterministic synthetic G2 presentation-diversity evaluation; "
                "not human-realism, cultural-validity, legal, native-file, "
                "production-fidelity, or outcome evidence."
            ),
        }


def _normalize_block_id(block_id: str) -> str:
    parts = block_id.split(".")
    if parts and parts[-1].isdigit():
        return ".".join((*parts[:-1], "<variant>"))
    return block_id


def build_corpus_diversity_artifacts(
    compilation: CaseCompilation,
    qualification_receipt: CaseCompilationQualificationReceipt,
    bundles: Iterable[QualifiedPersonaChannelRenderBundle],
) -> tuple[CorpusDiversityArtifact, ...]:
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
    rows: list[CorpusDiversityArtifact] = []
    for bundle in bundles_tuple:
        projection = compilation.renderer_projections[bundle.projection_index]
        section_sequence = tuple(
            section for section, _ in bundle.plan.section_plan
        )
        segment_geometry = tuple(
            (segment.section_id, segment.function)
            for segment in bundle.candidate.segments
        )
        assertion_positions = tuple(
            index
            for index, segment in enumerate(bundle.candidate.segments)
            if segment.function == "assertion"
        )
        normalized_blocks = tuple(
            _normalize_block_id(item)
            for item in bundle.plan.nonassertive_block_ids
        )
        style_operations = tuple(sorted(bundle.plan.style_operations))
        realized_operations = tuple(
            item
            for item in style_operations
            if item in _REALIZED_LEGACY_OPERATIONS
            or item.startswith(_REALIZED_OPERATION_PREFIXES)
        )
        skeleton = tuple(
            [
                f"section:{item}" for item in section_sequence
            ]
            + [
                f"segment:{section}:{function}"
                for section, function in segment_geometry
            ]
            + [f"operation:{item}" for item in realized_operations]
            + [f"block:{item}" for item in normalized_blocks]
        )
        presentation_payload = {
            "channel": projection.channel_kind,
            "sections": section_sequence,
            "segments": segment_geometry,
            "assertion_positions": assertion_positions,
            "operations": realized_operations,
            "blocks": normalized_blocks,
            "audience_mode": bundle.disposition.audience_mode,
            "compatibility": bundle.disposition.channel_compatibility,
        }
        assertion_trace = tuple(
            assertion_id
            for segment in bundle.candidate.segments
            for assertion_id in segment.assertion_ids
        )
        payload = {
            "matter_commitment": digest(
                {
                    "world": projection.world_namespace,
                    "matter": projection.matter_namespace,
                }
            ),
            "author_commitment": derive_actor_identity_commitment(
                projection, compilation.presentation_scope_commitment
            ),
            "organization_commitment": derive_organization_identity_commitment(
                projection, compilation.presentation_scope_commitment
            ),
            "culture_commitment": bundle.disposition.organization_culture_hash,
            "channel_kind": projection.channel_kind,
            "family_id": projection.family_id,
            "role_id": projection.persona_view.role_id,
            "effective_voice_signature": bundle.disposition.voice_signature,
            "effective_geometry_signature": (
                bundle.disposition.effective_geometry_signature
            ),
            "channel_contract_hash": bundle.contract.contract_hash,
            "section_sequence": section_sequence,
            "segment_geometry": segment_geometry,
            "assertion_positions": assertion_positions,
            "style_operation_ids": style_operations,
            "realized_operation_ids": realized_operations,
            "normalized_nonassertive_block_ids": normalized_blocks,
            "audience_mode": bundle.disposition.audience_mode,
            "channel_compatibility": bundle.disposition.channel_compatibility,
            "presentation_fingerprint": digest(presentation_payload),
            "semantic_skeleton_tokens": skeleton,
            "variant_id": bundle.plan.variant_id,
            "factual_trace_hash": digest(assertion_trace),
            "body_hash": digest(bundle.candidate.body),
            "qualified_bundle_hash": bundle.qualified_bundle_hash,
            "source_compilation_hash": compilation.compilation_hash,
            "synthetic_only": bundle.candidate.synthetic_only,
        }
        rows.append(
            CorpusDiversityArtifact(
                artifact_commitment=f"CDIV-{digest(payload)[:18]}",
                **payload,
            )
        )
    return tuple(rows)


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


def _pair_rates(
    rows: tuple[CorpusDiversityArtifact, ...],
    near_threshold: float,
) -> tuple[float, float]:
    changed_pairs = 0
    variant_only = 0
    cross_matter_pairs = 0
    near_pairs = 0
    for left, right in combinations(rows, 2):
        if left.body_hash != right.body_hash:
            changed_pairs += 1
            if (
                left.presentation_fingerprint
                == right.presentation_fingerprint
                and left.variant_id != right.variant_id
            ):
                variant_only += 1
        if left.matter_commitment != right.matter_commitment:
            cross_matter_pairs += 1
            similarity = _jaccard(
                left.semantic_skeleton_tokens,
                right.semantic_skeleton_tokens,
            )
            if similarity >= near_threshold:
                near_pairs += 1
    trivial_ratio = variant_only / changed_pairs if changed_pairs else 0.0
    near_rate = near_pairs / cross_matter_pairs if cross_matter_pairs else 0.0
    return trivial_ratio, near_rate


def _cross_author_distance(
    rows: tuple[CorpusDiversityArtifact, ...],
) -> tuple[float | None, str]:
    distances: list[float] = []
    for left, right in combinations(rows, 2):
        if left.author_commitment == right.author_commitment:
            continue
        distances.append(
            1.0 - _jaccard(
                left.realized_operation_ids,
                right.realized_operation_ids,
            )
        )
    if not distances:
        return None, "coverage_insufficient"
    return float(median(distances)), "eligible"


def _evaluate_corpus_diversity_artifacts(
    artifacts: Iterable[CorpusDiversityArtifact],
    policy: CorpusDiversityPolicy | None = None,
    *,
    qualified_binding_verified: bool = False,
) -> CorpusDiversityReport:
    policy = policy or CorpusDiversityPolicy()
    rows = tuple(artifacts)
    findings: list[DiversityFinding] = []

    def add(
        code: str,
        severity: Literal["error", "warning", "info"],
        subject: object,
        message: str,
    ) -> None:
        findings.append(
            DiversityFinding(
                code=code,
                severity=severity,
                subject_commitment=digest(subject),
                message=message,
            )
        )

    if rows and not qualified_binding_verified:
        add(
            "qualified_binding_unverified",
            "error",
            tuple(item.qualified_bundle_hash for item in rows),
            "raw diversity artifacts cannot self-attest qualified provenance",
        )

    commitments = [item.artifact_commitment for item in rows]
    if len(commitments) != len(set(commitments)):
        add(
            "duplicate_diversity_input",
            "error",
            commitments,
            "the same diversity artifact was supplied more than once",
        )
    if any(not item.synthetic_only for item in rows):
        add(
            "synthetic_boundary_missing",
            "error",
            commitments,
            "all diversity inputs must remain synthetic",
        )
    grouped: dict[str, list[CorpusDiversityArtifact]] = defaultdict(list)
    for row in rows:
        grouped[row.channel_kind].append(row)

    metrics: list[ChannelDiversityMetrics] = []
    eligible_count = 0
    insufficient_count = 0
    for channel, group_list in sorted(grouped.items()):
        group = tuple(group_list)
        eligible = len(group) >= policy.minimum_channel_size
        if eligible:
            eligible_count += 1
        else:
            insufficient_count += 1
            add(
                "coverage_insufficient",
                "info",
                channel,
                "channel group is below the diversity-policy sample floor",
            )
        voice_counts = Counter(
            item.effective_voice_signature for item in group
        )
        geometry_counts = Counter(
            item.effective_geometry_signature for item in group
        )
        combined_counts = Counter(
            (
                item.effective_voice_signature,
                item.effective_geometry_signature,
            )
            for item in group
        )
        presentation_count = len(
            {item.presentation_fingerprint for item in group}
        )
        largest_share = (
            max(combined_counts.values()) / len(group) if group else 0.0
        )
        presentation_ratio = (
            presentation_count / len(group) if group else 0.0
        )
        trivial_ratio, near_rate = _pair_rates(
            group,
            policy.near_template_threshold,
        )
        cross_author_distance, cross_author_status = _cross_author_distance(group)
        if eligible:
            if len(combined_counts) < policy.minimum_effective_families:
                add(
                    "effective_family_collapse",
                    "error",
                    (channel, tuple(sorted(combined_counts.items()))),
                    "channel lacks the required effective presentation families",
                )
            if largest_share > policy.maximum_family_share:
                add(
                    "effective_family_concentration",
                    "error",
                    (channel, largest_share),
                    "one effective presentation family exceeds the G2 ceiling",
                )
            if presentation_ratio < policy.minimum_presentation_ratio:
                add(
                    "meaningful_presentation_collapse",
                    "error",
                    (channel, presentation_ratio),
                    "meaningful presentation diversity is below the G2 floor",
                )
            if trivial_ratio > policy.trivial_variant_warning_threshold:
                add(
                    "trivial_variant_dominance",
                    "warning",
                    (channel, trivial_ratio),
                    "body changes are dominated by variant-only differences",
                )
            if near_rate > policy.near_template_warning_threshold:
                add(
                    "near_template_concentration",
                    "warning",
                    (channel, near_rate),
                    "cross-matter presentation skeletons remain highly similar",
                )
        if cross_author_distance is not None:
            if cross_author_distance < policy.cross_author_collapse_threshold:
                add(
                    "cross_author_collapse",
                    "warning",
                    (channel, cross_author_distance),
                    "declared presentation controls do not separate authors",
                )
            elif cross_author_distance > policy.cross_author_caricature_threshold:
                add(
                    "cross_author_caricature",
                    "warning",
                    (channel, cross_author_distance),
                    "author controls may be unrealistically over-separated",
                )
        metrics.append(
            ChannelDiversityMetrics(
                channel_kind=channel,
                artifact_count=len(group),
                eligible=eligible,
                effective_voice_family_count=len(voice_counts),
                effective_geometry_family_count=len(geometry_counts),
                effective_combined_family_count=len(combined_counts),
                presentation_family_count=presentation_count,
                largest_effective_family_share=round(largest_share, 6),
                meaningful_presentation_ratio=round(presentation_ratio, 6),
                trivial_variant_ratio=round(trivial_ratio, 6),
                near_template_pair_rate=round(near_rate, 6),
                cross_author_median_distance=(
                    None
                    if cross_author_distance is None
                    else round(cross_author_distance, 6)
                ),
                cross_author_status=cross_author_status,
            )
        )

    if eligible_count == 0:
        add(
            "corpus_coverage_insufficient",
            "error",
            tuple(sorted(grouped)),
            "no channel group meets the diversity-policy sample floor",
        )

    authors: dict[str, list[CorpusDiversityArtifact]] = defaultdict(list)
    organizations: dict[str, list[CorpusDiversityArtifact]] = defaultdict(list)
    for row in rows:
        authors[row.author_commitment].append(row)
        organizations[row.organization_commitment].append(row)
    author_groups = tuple(tuple(group) for group in authors.values() if len(group) >= 2)
    organization_groups = tuple(
        tuple(group) for group in organizations.values() if len(group) >= 2
    )
    author_inconsistencies = tuple(
        group
        for group in author_groups
        if len({item.effective_voice_signature for item in group}) != 1
    )
    organization_inconsistencies = tuple(
        group
        for group in organization_groups
        if len({item.culture_commitment for item in group}) != 1
    )
    for group in author_inconsistencies:
        add(
            "within_author_continuity_failure",
            "error",
            tuple(item.artifact_commitment for item in group),
            "one synthetic author has inconsistent realized voice families",
        )
    for group in organization_inconsistencies:
        add(
            "organization_culture_coherence_failure",
            "error",
            tuple(item.artifact_commitment for item in group),
            "one synthetic organization has inconsistent culture commitments",
        )

    sections_by_channel = {
        channel: {item.section_sequence for item in group}
        for channel, group in grouped.items()
    }
    representative_sections = {
        next(iter(sections))
        for sections in sections_by_channel.values()
        if sections
    }
    separation = (
        len(representative_sections) / len(sections_by_channel)
        if sections_by_channel
        else 0.0
    )
    if sections_by_channel and separation != 1.0:
        add(
            "cross_channel_schema_collapse",
            "error",
            tuple(sorted(sections_by_channel)),
            "active channels do not have distinct required section schemas",
        )
    qualified_rate = 1.0 if rows and qualified_binding_verified else 0.0
    factual_coverage = (
        sum(bool(item.factual_trace_hash) for item in rows) / len(rows)
        if rows
        else 0.0
    )
    if rows and factual_coverage != 1.0:
        add(
            "factual_trace_coverage_incomplete",
            "error",
            commitments,
            "every diversity artifact must retain a factual trace commitment",
        )
    input_commitment = digest(
        tuple(sorted(rows, key=lambda item: item.artifact_commitment))
    )
    payload = {
        "passed": (
            qualified_binding_verified
            and not any(item.severity == "error" for item in findings)
        ),
        "policy_hash": policy.policy_hash,
        "artifact_count": len(rows),
        "qualified_binding_rate": qualified_rate,
        "factual_trace_coverage": factual_coverage,
        "cross_channel_schema_separation": separation,
        "eligible_channel_count": eligible_count,
        "insufficient_channel_count": insufficient_count,
        "within_author_eligible_count": len(author_groups),
        "within_author_inconsistency_count": len(author_inconsistencies),
        "organization_eligible_count": len(organization_groups),
        "organization_inconsistency_count": len(organization_inconsistencies),
        "channel_metrics": tuple(metrics),
        "findings": tuple(findings),
        "input_commitment": input_commitment,
        "evaluator_revision": CORPUS_DIVERSITY_REVISION,
        "synthetic_only": True,
        "human_realism_validated": False,
        "native_fidelity_validated": False,
        "bodies_included": False,
    }
    return CorpusDiversityReport(
        report_id=f"CORPUS-DIVERSITY-{digest(payload)[:18]}",
        **payload,
    )


def evaluate_corpus_diversity(
    inputs: Iterable[QualifiedCorpusDiversityInput],
    policy: CorpusDiversityPolicy | None = None,
) -> CorpusDiversityReport:
    cases = tuple(inputs)
    rows: list[CorpusDiversityArtifact] = []
    for item in cases:
        if not isinstance(item, QualifiedCorpusDiversityInput):
            raise ValueError("qualified_corpus_diversity_input_type_invalid")
        rows.extend(
            build_corpus_diversity_artifacts(
                item.compilation,
                item.qualification_receipt,
                item.bundles,
            )
        )
    return _evaluate_corpus_diversity_artifacts(
        tuple(rows),
        policy,
        qualified_binding_verified=True,
    )


