from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import locale
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
from dataclasses import dataclass
from typing import Literal

from .hashio import digest


REPLAY_HARNESS_REVISION = "design-c-fresh-process-replay-g0c-v3"
ENVIRONMENT_LOCK_REVISION = "design-c-environment-lock-g0c-v1"
REPLAY_WORKER_REVISION = "design-c-replay-worker-g0c-v2"


@dataclass(frozen=True)
class EnvironmentLock:
    revision: str
    python_implementation: str
    python_version: str
    platform_system: str
    platform_machine: str
    byteorder: str
    filesystem_encoding: str
    preferred_encoding: str
    locale_value: str
    timezone_env: str
    python_hash_seed: str
    dependency_lock_hashes: tuple[tuple[str, str], ...]
    package_versions: tuple[tuple[str, str], ...]
    source_tree_hash: str
    source_module_count: int
    cassette_contract_revision: Literal["g2_attempt_cassette_v2"]
    contains_secrets: Literal[False] = False
    contains_case_identifiers: Literal[False] = False

    @property
    def environment_hash(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class ReplayObservation:
    worker_revision: str
    environment_hash: str
    input_commitment: str
    event_hash: str
    projection_hash: str
    denial_hash: str
    command_hash: str
    berean_hash: str
    finance_hash: str
    process_id: int
    run_ordinal: int
    launch_nonce_commitment: str
    external_effects: Literal[False]
    canonical_write: Literal[False]

    @property
    def replay_semantics_hash(self) -> str:
        return digest(
            {
                "worker_revision": self.worker_revision,
                "environment_hash": self.environment_hash,
                "input_commitment": self.input_commitment,
                "event_hash": self.event_hash,
                "projection_hash": self.projection_hash,
                "denial_hash": self.denial_hash,
                "command_hash": self.command_hash,
                "berean_hash": self.berean_hash,
                "finance_hash": self.finance_hash,
                "external_effects": self.external_effects,
                "canonical_write": self.canonical_write,
            }
        )


@dataclass(frozen=True)
class FreshProcessReplayReceipt:
    receipt_id: str
    harness_revision: str
    worker_revision: str
    environment_hash: str
    input_commitment: str
    replay_semantics_hash: str
    fresh_process_count: int
    unique_process_id_count: int
    verified_launch_count: int
    unique_launch_commitment_count: int
    launch_evidence: tuple[tuple[int, str], ...]
    launch_evidence_chain_hash: str
    all_semantics_identical: Literal[True]
    environment_lock_validated: Literal[True]
    stale_environment_rejected: Literal[True]
    subprocess_isolation_used: Literal[True]
    changed_input_same_hash_required: Literal[False]
    canonical_admission: Literal[False]
    canonical_write: Literal[False]
    external_effects: Literal[False]
    contains_case_identifiers: Literal[False]

    @property
    def receipt_hash(self) -> str:
        return digest(self)


class StaleReplayEnvironmentError(RuntimeError):
    pass


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _loaded_source_tree_hash(package_root: Path) -> tuple[str, int]:
    resolved_root = package_root.resolve()
    rows: list[tuple[str, str]] = []
    for module_name, module in sorted(sys.modules.items()):
        if not module_name.startswith("law_firm_digital_twin"):
            continue
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        path = Path(module_file).resolve()
        if path.suffix != ".py":
            continue
        try:
            relative = path.relative_to(resolved_root)
        except ValueError:
            continue
        rows.append((relative.as_posix(), _file_sha256(path)))
    if not rows:
        raise RuntimeError("replay_source_module_closure_empty")
    return digest(tuple(rows)), len(rows)


def build_environment_lock(repo_root: Path) -> EnvironmentLock:
    dependency_paths = (
        repo_root / "pyproject.toml",
        repo_root / "requirements" / "simulation.lock",
    )
    dependency_hashes = tuple(
        (path.relative_to(repo_root).as_posix(), _file_sha256(path))
        for path in dependency_paths
    )
    packages = []
    for package in ("simpy",):
        try:
            package_version = version(package)
        except PackageNotFoundError:
            package_version = "not-installed"
        packages.append((package, package_version))
    source_tree_hash, source_module_count = _loaded_source_tree_hash(
        repo_root / "src" / "law_firm_digital_twin"
    )
    return EnvironmentLock(
        revision=ENVIRONMENT_LOCK_REVISION,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        platform_system=platform.system(),
        platform_machine=platform.machine(),
        byteorder=sys.byteorder,
        filesystem_encoding=sys.getfilesystemencoding(),
        preferred_encoding=locale.getpreferredencoding(False),
        locale_value=locale.setlocale(locale.LC_ALL, None),
        timezone_env=os.environ.get("TZ", "UNSET"),
        python_hash_seed=os.environ.get("PYTHONHASHSEED", "UNSET"),
        dependency_lock_hashes=dependency_hashes,
        package_versions=tuple(packages),
        source_tree_hash=source_tree_hash,
        source_module_count=source_module_count,
        cassette_contract_revision="g2_attempt_cassette_v2",
        contains_secrets=False,
        contains_case_identifiers=False,
    )


def _worker_environment(
    repo_root: Path, run_ordinal: int, launch_nonce: str
) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
            "LC_ALL": "C",
            "LANG": "C",
            "LFDT_REPLAY_RUN_ORDINAL": str(run_ordinal),
            "LFDT_REPLAY_LAUNCH_NONCE": launch_nonce,
            "PYTHONPATH": str(repo_root / "src"),
        }
    )
    return environment


def run_replay_subprocess(
    repo_root: Path,
    *,
    run_ordinal: int,
    expected_environment_hash: str | None,
    timeout_seconds: int = 30,
) -> ReplayObservation:
    launch_nonce = secrets.token_hex(32)
    environment = _worker_environment(repo_root, run_ordinal, launch_nonce)
    if expected_environment_hash is not None:
        environment["LFDT_EXPECTED_ENVIRONMENT_HASH"] = expected_environment_hash
    completed = subprocess.run(
        [sys.executable, "-m", "law_firm_digital_twin.replay_worker"],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"replay_worker_nonjson:exit_{completed.returncode}:stderr_commitment_{digest(completed.stderr)}"
        ) from exc
    if completed.returncode == 3 and payload.get("error") == "stale_environment_or_dependency":
        raise StaleReplayEnvironmentError("stale_environment_or_dependency")
    if completed.returncode != 0:
        raise RuntimeError(
            f"replay_worker_failed:exit_{completed.returncode}:error_{payload.get('error', 'unknown')}"
        )
    expected_nonce_commitment = digest(launch_nonce)
    if payload.get("launch_nonce_commitment") != expected_nonce_commitment:
        raise RuntimeError("replay_launch_nonce_mismatch")
    if int(payload.get("run_ordinal", -1)) != run_ordinal:
        raise RuntimeError("replay_run_ordinal_mismatch")
    return ReplayObservation(
        worker_revision=str(payload["worker_revision"]),
        environment_hash=str(payload["environment_hash"]),
        input_commitment=str(payload["input_commitment"]),
        event_hash=str(payload["event_hash"]),
        projection_hash=str(payload["projection_hash"]),
        denial_hash=str(payload["denial_hash"]),
        command_hash=str(payload["command_hash"]),
        berean_hash=str(payload["berean_hash"]),
        finance_hash=str(payload["finance_hash"]),
        process_id=int(payload["process_id"]),
        run_ordinal=int(payload["run_ordinal"]),
        launch_nonce_commitment=expected_nonce_commitment,
        external_effects=False,
        canonical_write=False,
    )


def qualify_fresh_process_replay(
    repo_root: Path,
    *,
    run_count: int = 100,
    max_workers: int = 4,
) -> FreshProcessReplayReceipt:
    if run_count <= 1 or run_count > 1000:
        raise ValueError("replay_run_count_invalid")
    if max_workers <= 0 or max_workers > 8:
        raise ValueError("replay_worker_count_invalid")
    preflight = run_replay_subprocess(
        repo_root,
        run_ordinal=0,
        expected_environment_hash=None,
    )
    expected_environment_hash = preflight.environment_hash
    def run_one(ordinal: int) -> ReplayObservation:
        return run_replay_subprocess(
            repo_root,
            run_ordinal=ordinal,
            expected_environment_hash=expected_environment_hash,
        )

    with ThreadPoolExecutor(
        max_workers=min(max_workers, run_count)
    ) as executor:
        observations = tuple(executor.map(run_one, range(1, run_count + 1)))
    if any(item.environment_hash != expected_environment_hash for item in observations):
        raise ValueError("replay_environment_drift")
    semantics = {item.replay_semantics_hash for item in observations}
    if len(semantics) != 1:
        raise ValueError("unchanged_input_replay_mismatch")
    input_commitments = {item.input_commitment for item in observations}
    if len(input_commitments) != 1:
        raise ValueError("replay_input_commitment_drift")
    stale_rejected = False
    try:
        run_replay_subprocess(
            repo_root,
            run_ordinal=run_count + 1,
            expected_environment_hash="0" * 64,
        )
    except StaleReplayEnvironmentError:
        stale_rejected = True
    if not stale_rejected:
        raise ValueError("stale_environment_not_rejected")
    semantics_hash = next(iter(semantics))
    input_commitment = next(iter(input_commitments))
    process_ids = {item.process_id for item in observations}
    launch_evidence = tuple(
        (item.run_ordinal, item.launch_nonce_commitment)
        for item in observations
    )
    launch_commitments = {item[1] for item in launch_evidence}
    launch_evidence_chain_hash = digest(launch_evidence)
    if len(launch_commitments) != run_count:
        raise ValueError("fresh_process_launch_evidence_incomplete")
    if not process_ids or len(process_ids) > run_count:
        raise ValueError("process_id_telemetry_invalid")
    payload = {
        "harness": REPLAY_HARNESS_REVISION,
        "worker": REPLAY_WORKER_REVISION,
        "environment": expected_environment_hash,
        "input": input_commitment,
        "semantics": semantics_hash,
        "runs": run_count,
        "process_ids": len(process_ids),
        "verified_launches": run_count,
        "launch_commitments": len(launch_commitments),
        "launch_evidence_chain": launch_evidence_chain_hash,
    }
    return FreshProcessReplayReceipt(
        receipt_id=f"REPLAY-QUAL-{digest(payload)[:18]}",
        harness_revision=REPLAY_HARNESS_REVISION,
        worker_revision=REPLAY_WORKER_REVISION,
        environment_hash=expected_environment_hash,
        input_commitment=input_commitment,
        replay_semantics_hash=semantics_hash,
        fresh_process_count=run_count,
        unique_process_id_count=len(process_ids),
        verified_launch_count=run_count,
        unique_launch_commitment_count=len(launch_commitments),
        launch_evidence=launch_evidence,
        launch_evidence_chain_hash=launch_evidence_chain_hash,
        all_semantics_identical=True,
        environment_lock_validated=True,
        stale_environment_rejected=True,
        subprocess_isolation_used=True,
        changed_input_same_hash_required=False,
        canonical_admission=False,
        canonical_write=False,
        external_effects=False,
        contains_case_identifiers=False,
    )

