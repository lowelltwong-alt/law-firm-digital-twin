# Candidate lesson: cross-platform absolute-path validation

Status: locally verified candidate; DAD transport unavailable  
Evidence date: 2026-07-18

## Surprise

`PurePosixPath("C:/lfdt-data/output.json").is_absolute()` is false. A validator
that normalizes separators and then checks only `PurePosixPath` can therefore
accept a Windows drive-qualified path as repository-relative.

## Repair

For provider-neutral job/write-scope contracts, reject a path when either
`PurePosixPath(path).is_absolute()` or `PureWindowsPath(path).is_absolute()` is
true, and check parent traversal under both interpretations. Keep a hostile
Windows-drive test even when CI runs on another operating system.

## Evidence

- `tests/test_design_c_registry.py`
- `tests/test_campaign_spec.py::test_windows_absolute_output_path_is_rejected`
- `src/law_firm_digital_twin/design_c_validator.py`
- `campaigns/g2-scale-v1/checks/validate_manifest_contract.py`

The focused validator suites changed from one failing Windows-path attack to 22
passing checks. This lesson contains no private data or raw command payload.
