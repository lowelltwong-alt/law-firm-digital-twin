from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns" / "g2-scale-v1" / "campaign.json"
VALIDATOR = ROOT / "campaigns" / "g2-scale-v1" / "checks" / "validate_manifest_contract.py"
SPEC = importlib.util.spec_from_file_location("g2_scale_manifest_validator", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def all_jobs(data: dict[str, object]) -> list[dict[str, object]]:
    return MODULE.jobs(data)


def test_current_campaign_manifest_is_valid_and_specification_only() -> None:
    data = load_manifest()
    assert MODULE.validate(data) == []
    assert data["execution"]["mode"] == "specification_only"
    assert data["execution"]["launch_command"] == "not-authorized"
    assert len(all_jobs(data)) == 10
    jobs = {item["id"]: item for item in all_jobs(data)}
    assert jobs["J130"]["depends_on"] == ["J100", "J110", "J120"]
    assert jobs["J200"]["depends_on"] == ["J130"]
    assert jobs["J210"]["depends_on"] == ["J200"]


def test_unattended_mode_fails_without_every_launch_receipt() -> None:
    data = load_manifest()
    data["execution"]["mode"] = "unattended"
    errors = MODULE.validate(data)
    assert any("unattended mode lacks" in item for item in errors)


def test_missing_mandatory_stop_fails() -> None:
    data = load_manifest()
    data["stop_conditions"] = [
        item for item in data["stop_conditions"] if item["code"] != "security_or_privacy"
    ]
    errors = MODULE.validate(data)
    assert any("missing mandatory stops" in item for item in errors)


def test_worker_cannot_write_controller_state() -> None:
    data = load_manifest()
    job = all_jobs(data)[1]
    job["outputs"] = [".campaign-state/g2-scale-v1/forged.json"]
    job["allowed_paths"] = list(job["outputs"])
    errors = MODULE.validate(data)
    assert any("worker output enters controller state" in item for item in errors)


def test_writer_cannot_check_its_own_job() -> None:
    data = load_manifest()
    job = all_jobs(data)[1]
    job["checker_role"] = job["owner_role"]
    job["acceptance"][0]["checker_role"] = job["owner_role"]
    errors = MODULE.validate(data)
    assert any("writer and checker must differ" in item for item in errors)
    assert any("gate checker equals writer" in item for item in errors)


def test_dependency_cycle_fails() -> None:
    data = load_manifest()
    job_list = all_jobs(data)
    job_list[0]["depends_on"] = [job_list[-1]["id"]]
    errors = MODULE.validate(data)
    assert any("dependency cycle" in item for item in errors)


def test_overlapping_job_output_scope_fails() -> None:
    data = load_manifest()
    job_list = all_jobs(data)
    stolen = job_list[1]["outputs"][0]
    job_list[2]["outputs"] = [stolen]
    job_list[2]["allowed_paths"] = [stolen]
    errors = MODULE.validate(data)
    assert any("write scope collision" in item for item in errors)


def test_human_gate_cannot_auto_advance() -> None:
    data = load_manifest()
    first = all_jobs(data)[0]
    assert first["acceptance"][0]["type"] == "human"
    first["auto_advance"] = True
    errors = MODULE.validate(data)
    assert any("human gate cannot auto-advance" in item for item in errors)




def test_local_validator_never_authorizes_unattended_execution() -> None:
    data = load_manifest()
    data["execution"]["mode"] = "unattended"
    for field in (
        "launch_command",
        "shutdown_command",
        "qualification_evidence",
        "dry_run_evidence",
        "authorization_receipt",
        "independent_launch_review",
    ):
        data["execution"][field] = f"forged-{field}"
    errors = MODULE.validate(data)
    assert any("cannot authorize unattended" in item for item in errors)


def test_malformed_graph_returns_structured_errors_instead_of_crashing() -> None:
    data = load_manifest()
    data["phases"][0] = "malformed"
    errors = MODULE.validate(data)
    assert any("phase[0] must be an object" in item for item in errors)

def test_windows_absolute_output_path_is_rejected() -> None:
    data = load_manifest()
    job = all_jobs(data)[1]
    job["outputs"] = ["C:/lfdt-data/forged.json"]
    job["allowed_paths"] = list(job["outputs"])
    errors = MODULE.validate(data)
    assert any("unsafe output:" in item for item in errors)
