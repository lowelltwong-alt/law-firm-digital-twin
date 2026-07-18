from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.corpus_auditor import (
    audit_persona_channel_corpus,
    build_corpus_audit_artifacts,
)
from law_firm_digital_twin.corpus_diversity_evaluator import (
    QualifiedCorpusDiversityInput,
    evaluate_corpus_diversity,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.persona_channel_renderer import (
    PERSONA_CHANNEL_ADAPTER_REVISION,
    render_persona_channel_batch,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


FIXTURE_REVISION = "g2-channel-fixture-v1"


def build_payloads(
    *, seed: str, count: int
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if count < 1:
        raise ValueError("count_must_be_positive")
    compilations = compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    qualification_receipts = tuple(
        qualify_case_compilation(compilation)
        for compilation in compilations
    )
    rendered_groups = tuple(
        (
            compilation,
            qualification_receipt,
            render_persona_channel_batch(
                compilation,
                qualification_receipt,
            ),
        )
        for compilation, qualification_receipt in zip(
            compilations,
            qualification_receipts,
            strict=True,
        )
    )
    rendered = tuple(
        (
            compilation,
            qualification_receipt,
            bundle.projection_index,
            bundle,
        )
        for compilation, qualification_receipt, bundles in rendered_groups
        for bundle in bundles
    )
    audit_inputs = tuple(
        audit_artifact
        for compilation, qualification_receipt, bundles in rendered_groups
        for audit_artifact in build_corpus_audit_artifacts(
            compilation,
            qualification_receipt,
            bundles,
        )
    )
    audit_report = audit_persona_channel_corpus(audit_inputs)
    if not audit_report.passed:
        codes = sorted(
            item.code
            for item in audit_report.findings
            if item.severity == "error"
        )
        raise ValueError("corpus_audit_failed:" + ",".join(codes))
    diversity_inputs = tuple(
        QualifiedCorpusDiversityInput(
            compilation=compilation,
            qualification_receipt=qualification_receipt,
            bundles=tuple(bundles),
        )
        for compilation, qualification_receipt, bundles in rendered_groups
    )
    diversity_report = evaluate_corpus_diversity(diversity_inputs)
    if not diversity_report.passed:
        codes = sorted(
            item.code
            for item in diversity_report.findings
            if item.severity == "error"
        )
        raise ValueError("corpus_diversity_failed:" + ",".join(codes))
    channel_counts = Counter(
        compilation.renderer_projections[projection_index].channel_kind
        for compilation, _, projection_index, _ in rendered
    )
    artifact_rows = tuple(
        {
            "public_artifact_id": (
                "PUBLIC-ARTIFACT-"
                + digest(
                    {
                        "projection": projection.projection_hash,
                        "candidate": bundle.candidate.candidate_hash,
                    }
                )[:18]
            ),
            "channel_kind": projection.channel_kind,
            "family_id": projection.family_id,
            "rendered_media_type": bundle.candidate.rendered_media_type,
            "simulated_target_native_format": (
                bundle.candidate.simulated_target_native_format
            ),
            "variant_id": bundle.plan.variant_id,
            "candidate_hash": bundle.candidate.candidate_hash,
            "composition_plan_hash": bundle.plan.plan_hash,
            "qualified_bundle_hash": bundle.qualified_bundle_hash,
            "local_shape_receipt_hash": bundle.local_shape_receipt.receipt_hash,
            "composition_validated": True,
            "factual_authority_validated": False,
            "lineage_graph_validated": False,
            "canonical_admission": False,
            "synthetic_only": True,
        }
        for compilation, _, projection_index, bundle in rendered
        for projection in (
            compilation.renderer_projections[projection_index],
        )
    )
    manifest = {
        "fixture_revision": FIXTURE_REVISION,
        "adapter_revision": PERSONA_CHANNEL_ADAPTER_REVISION,
        "seed_commitment": digest(
            {"fixture_revision": FIXTURE_REVISION, "seed": seed}
        ),
        "case_count": len(compilations),
        "artifact_count": len(rendered),
        "channel_counts": dict(sorted(channel_counts.items())),
        "unique_candidate_count": len(
            {
                bundle.candidate.candidate_hash
                for _, _, _, bundle in rendered
            }
        ),
        "qualification_receipt_commitments": tuple(
            receipt.receipt_hash for receipt in qualification_receipts
        ),
        "operating_projection_commitments": tuple(
            compilation.operating.projection_hash
            for compilation in compilations
        ),
        "artifacts": artifact_rows,
        "diversity_report_id": diversity_report.report_id,
        "diversity_policy_hash": diversity_report.policy_hash,
        "synthetic_only": True,
        "non_predictive": True,
        "bodies_included": False,
        "scope_statement": (
            "Parallel deterministic G2 text fixture. It does not replace the "
            "base renderer or claim native-file, legal, or production fidelity."
        ),
    }
    return (
        manifest,
        audit_report.public_summary(),
        diversity_report.public_summary(),
    )


def build_fixture(
    *,
    seed: str,
    count: int,
    output_root: Path,
) -> tuple[Path, Path, Path]:
    manifest, audit_summary, diversity_summary = build_payloads(
        seed=seed,
        count=count,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "render-manifest.json"
    audit_path = output_root / "corpus-audit-summary.json"
    diversity_path = output_root / "corpus-diversity-summary.json"
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    audit_path.write_text(
        canonical_json(audit_summary) + "\n",
        encoding="utf-8",
    )
    diversity_path.write_text(
        canonical_json(diversity_summary) + "\n",
        encoding="utf-8",
    )
    return manifest_path, audit_path, diversity_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="g2-scale-v1-ten")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("generated/g2-channel-v1"),
    )
    args = parser.parse_args()
    manifest_path, audit_path, diversity_path = build_fixture(
        seed=args.seed,
        count=args.count,
        output_root=args.output_root,
    )
    print(f"WROTE {manifest_path}")
    print(f"WROTE {audit_path}")
    print(f"WROTE {diversity_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

