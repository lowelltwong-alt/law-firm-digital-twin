from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from law_firm_digital_twin.replay_qualification import (  # noqa: E402
    qualify_fresh_process_replay,
)


OUTPUT = ROOT / "generated" / "design-c-e2-replay-v1"


def build_public_summary(run_count: int) -> dict[str, object]:
    receipt = qualify_fresh_process_replay(ROOT, run_count=run_count)
    return {
        "schema": "design_c_e2_replay_public_summary_v1",
        "run_count": receipt.fresh_process_count,
        "unique_process_id_count": receipt.unique_process_id_count,
        "verified_launch_count": receipt.verified_launch_count,
        "unique_launch_commitment_count": (
            receipt.unique_launch_commitment_count
        ),
        "all_semantics_identical": receipt.all_semantics_identical,
        "environment_lock_validated": receipt.environment_lock_validated,
        "stale_environment_rejected": receipt.stale_environment_rejected,
        "subprocess_isolation_used": receipt.subprocess_isolation_used,
        "changed_input_same_hash_required": receipt.changed_input_same_hash_required,
        "canonical_admission": receipt.canonical_admission,
        "canonical_write": receipt.canonical_write,
        "external_effects": receipt.external_effects,
        "contains_case_identifiers": receipt.contains_case_identifiers,
        "contains_replay_or_environment_commitments": False,
        "nonjoinable": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()
    summary = build_public_summary(args.runs)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# Design C E-2 Replay Fixture\n\n"
        "Aggregate qualification evidence only. Hashes, seeds, case identifiers, "
        "cassettes, and environment commitments are intentionally excluded.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
