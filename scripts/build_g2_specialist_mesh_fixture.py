from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.case_compiler import (
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.hashio import canonical_json, digest
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack
from law_firm_digital_twin.specialist_mesh_validator import (
    QualifiedSpecialistMeshInput,
    evaluate_specialist_mesh_corpus,
)


FIXTURE_REVISION = "g2-specialist-mesh-fixture-v1"


def build_payload(*, seed: str, count: int) -> dict[str, object]:
    if count < 1:
        raise ValueError("count_must_be_positive")
    compilations = compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    report = evaluate_specialist_mesh_corpus(
        tuple(
            QualifiedSpecialistMeshInput(
                compilation=compilation,
                qualification_receipt=qualify_case_compilation(compilation),
            )
            for compilation in compilations
        )
    )
    return {
        "fixture_revision": FIXTURE_REVISION,
        "seed_commitment": digest(
            {"fixture_revision": FIXTURE_REVISION, "seed": seed}
        ),
        **report.public_summary(),
    }


def write_fixture(output: Path, payload: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "mesh-report.json").write_text(
        canonical_json(payload) + "\n",
        encoding="utf-8",
    )
    (output / "README.md").write_text(
        "# G2 Artifact Specialist Mesh Fixture\n\n"
        "This public-safe aggregate fixture proves deterministic binding of each "
        "active G2 artifact to provider-neutral planner, writer, renderer, and "
        "independent-checker contracts. It does not contain document bodies, raw "
        "actor or matter identifiers, sealed labels, or private source data.\n\n"
        "All specialist assignments remain contract-only and unexecuted in this "
        "fixture. The existing deterministic G2 renderer remains the only artifact "
        "generation path, and no legal, factual, native-file, or canonical-admission "
        "claim is made.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="g2-specialist-mesh-v1-ten")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "g2-specialist-mesh-v1",
    )
    args = parser.parse_args()
    write_fixture(args.output, build_payload(seed=args.seed, count=args.count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
