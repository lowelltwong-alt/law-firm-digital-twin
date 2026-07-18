from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.case_compiler import (  # noqa: E402
    compile_population_fixture,
    qualify_case_compilation,
)
from law_firm_digital_twin.employment_lifecycle_catalog import (  # noqa: E402
    build_employment_lifecycle_document_catalog,
)
from law_firm_digital_twin.hashio import canonical_json  # noqa: E402
from law_firm_digital_twin.litigation_lifecycle_validator import (  # noqa: E402
    validate_public_dossier_catalog_summary,
    validate_qualified_matter_dossier_blueprint,
)
from law_firm_digital_twin.matter_dossier_planner import (  # noqa: E402
    QualifiedDossierSummaryInput,
    build_public_dossier_catalog_summary,
    build_qualified_matter_dossier_blueprint,
)
from law_firm_digital_twin.rules import placeholder_data_first_rule_pack  # noqa: E402


def build_payload() -> dict[str, object]:
    catalog = build_employment_lifecycle_document_catalog()
    compilations = compile_population_fixture(
        seed="g2-employment-dossier-public-v1",
        count=5,
        rule_pack=placeholder_data_first_rule_pack(),
    )
    qualified = tuple(
        (item, qualify_case_compilation(item)) for item in compilations
    )
    blueprints = tuple(
        build_qualified_matter_dossier_blueprint(compilation, receipt, catalog)
        for compilation, receipt in qualified
    )
    for (compilation, receipt), blueprint in zip(qualified, blueprints):
        report = validate_qualified_matter_dossier_blueprint(
            blueprint,
            compilation,
            receipt,
            catalog,
        )
        if not report.passed:
            raise ValueError(f"dossier_blueprint_invalid:{report.findings}")
    qualified_inputs = tuple(
        QualifiedDossierSummaryInput(
            compilation=compilation,
            qualification_receipt=receipt,
            blueprint=blueprint,
        )
        for (compilation, receipt), blueprint in zip(qualified, blueprints)
    )
    summary = build_public_dossier_catalog_summary(qualified_inputs, catalog)
    report = validate_public_dossier_catalog_summary(summary, qualified_inputs, catalog)
    if not report.passed:
        raise ValueError(f"public_dossier_summary_invalid:{report.findings}")
    return asdict(summary)


def write_catalog(output: Path, payload: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "catalog_summary.json").write_text(
        canonical_json(payload) + "\n",
        encoding="utf-8",
    )
    (output / "README.md").write_text(
        "# G2 Employment-Defense Matter Dossier Catalog\n\n"
        "This public-safe aggregate summarizes a non-rendering, nonexecuting "
        "employment-defense matter-file blueprint. It contains counts and "
        "commitments only. The typed source catalog covers referral, conflicts, "
        "carrier management, preservation, investigation, pleadings, discovery, "
        "eDiscovery, depositions, experts, motions, settlement, mediation, "
        "arbitration design, trial, appeal, billing, reductions, billing appeals, "
        "payments, write-offs, closure, and retention.\n\n"
        "It contains no document bodies, case facts, actor identities, source "
        "rows, selected route, outcome, financial amounts, prompts, or runtime "
        "execution. It admits no sources or legal rules and makes no legal-"
        "compliance, court-format, native-fidelity, or real-world prediction "
        "claim. Branch activation remains kernel-event-only.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "g2-employment-dossier-plan-v1",
    )
    args = parser.parse_args()
    write_catalog(args.output, build_payload())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

