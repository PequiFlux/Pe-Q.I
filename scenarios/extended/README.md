# Extended Scenarios

Area for future scenarios that should not expand the public showcase pack.

Use this tree for experiments, stress cases, and failure-path cases after the main
`scenarios/cases/` pack reached 20 showcase scenarios.

Suggested layout:

- `stress/`: larger queues, latency probes, scale and robustness fixtures.
- `failure/`: malformed inputs, missing dependencies, invalid documents, and fail-closed cases.

Rules:

- Do not add new showcase cases to `scenarios/cases/` without an explicit decision to change the public sample contract.
- Do not add extended scenarios to `scenarios/manifest.json`; keep the main manifest aligned with the 20-case public pack.
- Extended manifests, if needed, should live under this directory and should write reports to `bench/reports/extended/`, `bench/reports/extended-sample/`, or a temporary local directory.
