from __future__ import annotations

import json
import os
from pathlib import Path

from .berean import BereanAuditor
from .g2 import build_g2_attempt_cassette, execute_g2_attempt_cassette
from .hashio import digest
from .models import Arm, Route
from .replay_qualification import REPLAY_WORKER_REVISION, build_environment_lock


PROTECTED_REPLAY_SEED = "design-c-e2-protected-fixture-v1"


def build_replay_observation() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    environment_lock = build_environment_lock(repo_root)
    launch_nonce = os.environ.get("LFDT_REPLAY_LAUNCH_NONCE", "")
    if len(launch_nonce) != 64:
        return {
            "error": "launch_nonce_missing_or_invalid",
            "worker_revision": REPLAY_WORKER_REVISION,
        }
    expected = os.environ.get("LFDT_EXPECTED_ENVIRONMENT_HASH")
    if expected is not None and expected != environment_lock.environment_hash:
        return {
            "error": "stale_environment_or_dependency",
            "worker_revision": REPLAY_WORKER_REVISION,
        }
    serialized = build_g2_attempt_cassette(
        PROTECTED_REPLAY_SEED,
        Arm.AI_FIRST,
        Route.TRIAL_APPEAL,
    )
    run_ordinal = int(os.environ.get("LFDT_REPLAY_RUN_ORDINAL", "0"))
    kernel, commands = execute_g2_attempt_cassette(
        serialized,
        run_suffix=f"e2-{run_ordinal}",
    )
    audit = BereanAuditor().audit(kernel)
    return {
        "worker_revision": REPLAY_WORKER_REVISION,
        "environment_hash": environment_lock.environment_hash,
        "input_commitment": digest(json.loads(serialized)),
        "event_hash": kernel.canonical_event_hash(),
        "projection_hash": kernel.projection_hash(),
        "denial_hash": kernel.denial_hash(),
        "command_hash": digest(commands),
        "berean_hash": audit.report_hash,
        "finance_hash": digest(kernel.projection.finance),
        "process_id": os.getpid(),
        "run_ordinal": run_ordinal,
        "launch_nonce_commitment": digest(launch_nonce),
    }


def main() -> int:
    payload = build_replay_observation()
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if payload.get("error") == "stale_environment_or_dependency":
        return 3
    return 4 if payload.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
