from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.case_compiler import (
    build_public_blueprint_receipts,
    build_public_corpus_manifest,
    compile_population_fixture,
)
from law_firm_digital_twin.case_manifest import build_population_blueprints
from law_firm_digital_twin.hashio import canonical_json
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack


def build_fixture(
    *,
    seed: str,
    count: int,
    output_root: Path,
) -> tuple[Path, Path]:
    if count < 1:
        raise ValueError("count_must_be_positive")
    blueprints = build_population_blueprints(seed, count)
    compilations = compile_population_fixture(
        seed=seed,
        count=count,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    blueprint_receipts = build_public_blueprint_receipts(blueprints)
    corpus_manifest = build_public_corpus_manifest(compilations)
    output_root.mkdir(parents=True, exist_ok=True)
    blueprint_path = output_root / "blueprints.json"
    manifest_path = output_root / "corpus-manifest.json"
    blueprint_path.write_text(
        canonical_json(blueprint_receipts) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        canonical_json(corpus_manifest) + "\n",
        encoding="utf-8",
    )
    return blueprint_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="g2-scale-v1-ten")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("generated/g2-scale-v1"),
    )
    args = parser.parse_args()
    blueprint_path, manifest_path = build_fixture(
        seed=args.seed,
        count=args.count,
        output_root=args.output_root,
    )
    print(f"WROTE {blueprint_path}")
    print(f"WROTE {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

