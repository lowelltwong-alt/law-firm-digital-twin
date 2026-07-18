from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.domain_pack_design_validator import (
    build_public_domain_pack_design_catalog,
)
from law_firm_digital_twin.domain_pack_designs import build_design_only_domain_packs
from law_firm_digital_twin.hashio import canonical_json


def build_payload() -> dict[str, object]:
    return build_public_domain_pack_design_catalog(build_design_only_domain_packs())


def write_catalog(output: Path, payload: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "catalog.json").write_text(
        canonical_json(payload) + "\n",
        encoding="utf-8",
    )
    (output / "README.md").write_text(
        "# G2 Design-Only Litigation Domain-Pack Catalog\n\n"
        "This public-safe catalog summarizes future insurance-defense evidence, "
        "expert, persona, organization, and lifecycle blueprints. Every pack is "
        "design-only, synthetic-only, source-empty, learning-ineligible, and "
        "runtime-disabled.\n\n"
        "The catalog does not include document bodies, case facts, persona states, "
        "source rows, credentials, prompts, or activation receipts. It cannot be "
        "used by the compiler or artifact-specialist mesh and does not authorize "
        "another case family, source ingestion, legal or medical claims, G3 "
        "fidelity, or runtime specialist execution.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "g2-domain-pack-designs-v1",
    )
    args = parser.parse_args()
    write_catalog(args.output, build_payload())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
