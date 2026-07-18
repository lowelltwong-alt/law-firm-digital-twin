from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


REQUIRED_STOPS = {
    "user_interrupt",
    "budget_exhausted",
    "authority_boundary",
    "human_gate_required",
    "repeated_failure",
    "gold_standard_failure",
    "security_or_privacy",
    "dependency_stale",
    "write_conflict",
    "validation_inconclusive",
}
RESULTS = {"pass", "fail_repairable", "fail_terminal", "blocked_human", "inconclusive"}
CONTROLLER_PREFIX = ".campaign-state/g2-scale-v1/"


def jobs(data: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    phases = data.get("phases", [])
    if not isinstance(phases, list):
        return found
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        waves = phase.get("waves", [])
        if not isinstance(waves, list):
            continue
        for wave in waves:
            if not isinstance(wave, dict):
                continue
            subwaves = wave.get("subwaves", [])
            if not isinstance(subwaves, list):
                continue
            for subwave in subwaves:
                if isinstance(subwave, dict) and isinstance(subwave.get("jobs"), list):
                    found.extend(item for item in subwave["jobs"] if isinstance(item, dict))
    return found



def graph_shape_errors(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    phases = data.get("phases")
    if not isinstance(phases, list):
        return ["phases must be a list"]
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            errors.append(f"phase[{phase_index}] must be an object")
            continue
        waves = phase.get("waves")
        if not isinstance(waves, list):
            errors.append(f"phase[{phase_index}].waves must be a list")
            continue
        for wave_index, wave in enumerate(waves):
            if not isinstance(wave, dict):
                errors.append(f"phase[{phase_index}].wave[{wave_index}] must be an object")
                continue
            subwaves = wave.get("subwaves")
            if not isinstance(subwaves, list):
                errors.append(f"phase[{phase_index}].wave[{wave_index}].subwaves must be a list")
                continue
            for subwave_index, subwave in enumerate(subwaves):
                prefix = f"phase[{phase_index}].wave[{wave_index}].subwave[{subwave_index}]"
                if not isinstance(subwave, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                items = subwave.get("jobs")
                if not isinstance(items, list):
                    errors.append(f"{prefix}.jobs must be a list")
                    continue
                for job_index, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append(f"{prefix}.job[{job_index}] must be an object")
    return errors


def safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(normalized)
    return (
        not posix_path.is_absolute()
        and not windows_path.is_absolute()
        and ".." not in posix_path.parts
        and ".." not in windows_path.parts
        and str(posix_path) not in {"", "."}
    )


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be an object"]
    if data.get("schema_version") != "long_run_campaign.v2":
        errors.append("schema_version must be long_run_campaign.v2")
    execution = data.get("execution", {})
    if not isinstance(execution, dict):
        errors.append("execution must be an object")
        execution = {}
    if execution.get("mode") not in {"specification_only", "unattended"}:
        errors.append("execution.mode is invalid")
    if execution.get("mode") == "specification_only":
        for field in ("launch_command", "shutdown_command", "qualification_evidence", "dry_run_evidence", "authorization_receipt", "independent_launch_review"):
            if execution.get(field) != "not-authorized":
                errors.append(f"specification_only requires {field}=not-authorized")
    elif execution.get("mode") == "unattended":
        errors.append("local specification validator cannot authorize unattended execution")
        for field in ("launch_command", "shutdown_command", "qualification_evidence", "dry_run_evidence", "authorization_receipt", "independent_launch_review"):
            if execution.get(field) in {None, "", "not-authorized"}:
                errors.append(f"unattended mode lacks {field}")

    declared_stops = {item.get("code") for item in data.get("stop_conditions", []) if isinstance(item, dict)}
    missing_stops = REQUIRED_STOPS - declared_stops
    if missing_stops:
        errors.append(f"missing mandatory stops: {sorted(missing_stops)}")

    errors.extend(graph_shape_errors(data))
    all_jobs = jobs(data)
    ids = [item.get("id") for item in all_jobs]
    if any(not isinstance(item, str) or not item for item in ids):
        errors.append("every job needs an id")
    if len(ids) != len(set(ids)):
        errors.append("job ids must be unique")
    known = set(ids)
    output_owner: dict[str, str] = {}
    graph: dict[str, tuple[str, ...]] = {}
    for item in all_jobs:
        job_id = str(item.get("id", "unknown"))
        dependencies = tuple(item.get("depends_on", ()))
        graph[job_id] = dependencies
        unknown = sorted(set(dependencies) - known)
        if unknown:
            errors.append(f"{job_id} has unknown dependencies: {unknown}")
        if item.get("owner_role") == item.get("checker_role"):
            errors.append(f"{job_id} writer and checker must differ")
        if item.get("max_attempts") != 2 or item.get("repair_limit") != 1:
            errors.append(f"{job_id} must use one original plus one repair")
        if item.get("retry_policy", {}).get("same_state_deterministic_retry") is not False:
            errors.append(f"{job_id} permits same-state deterministic retry")
        outputs = item.get("outputs", [])
        allowed = item.get("allowed_paths", [])
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"{job_id} has no outputs")
            continue
        for output in outputs:
            if not safe_relative(output):
                errors.append(f"{job_id} has unsafe output: {output}")
            if output not in allowed:
                errors.append(f"{job_id} output is outside its allowed paths: {output}")
            if str(output).replace("\\", "/").startswith(CONTROLLER_PREFIX):
                errors.append(f"{job_id} worker output enters controller state")
            prior = output_owner.get(str(output))
            if prior and prior != job_id:
                errors.append(f"write scope collision: {prior} and {job_id} own {output}")
            output_owner[str(output)] = job_id
        acceptance = item.get("acceptance", [])
        if not acceptance:
            errors.append(f"{job_id} has no acceptance gate")
        for gate in acceptance:
            if gate.get("checker_role") == item.get("owner_role"):
                errors.append(f"{job_id} gate checker equals writer")
            if set(gate.get("result_semantics", {})) != RESULTS:
                errors.append(f"{job_id} gate result semantics are incomplete")
            evidence = gate.get("evidence")
            if not safe_relative(evidence) or not str(evidence).replace("\\", "/").startswith("checks/g2-scale-v1/"):
                errors.append(f"{job_id} gate evidence is outside checks")
            if gate.get("type") == "human" and item.get("auto_advance") is not False:
                errors.append(f"{job_id} human gate cannot auto-advance")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"dependency cycle includes {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, ()):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)

    budgets = data.get("budgets", {})
    if budgets.get("max_parallel_jobs", 0) > 3:
        errors.append("parallelism exceeds the reviewed ceiling of 3")
    if budgets.get("max_attempts_total", 0) < len(all_jobs) * 2:
        errors.append("campaign attempt budget cannot fund declared job attempts")
    mesh = data.get("specialist_mesh", {})
    if mesh.get("truth_authority") != "world-kernel-only":
        errors.append("specialist mesh truth authority must be world-kernel-only")
    if data.get("campaign_id") != "law-firm-digital-twin-g2-scale-v1":
        errors.append("unexpected campaign identity")
    return list(dict.fromkeys(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 2
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"INVALID: {len(errors)} error(s)")
        return 1
    print("VALID: g2-scale-v1 specification; execution remains unauthorized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

