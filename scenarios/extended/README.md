# Extended Scenarios

Area for future scenarios that should not expand the public showcase pack.

Use this tree for experiments, stress cases, and failure-path cases after the main
`scenarios/cases/` pack reached 20 showcase scenarios.

Suggested layout:

- `stress/`: larger queues, latency probes, scale and robustness fixtures.
- `failure/`: malformed inputs, missing dependencies, invalid documents, and fail-closed cases.
- `public_train/`: B1 training split with 180 generated cases.
- `public_dev/`: B1 development split with 60 generated cases.
- `public_test_frozen/`: B1 public frozen test split with 100 generated cases.
- `private_holdout/`: B1 internal holdout split with 60 generated cases.

Rules:

- Do not add new showcase cases to `scenarios/cases/` without an explicit decision to change the public sample contract.
- Do not add extended scenarios to `scenarios/manifest.json`; keep the main manifest aligned with the 20-case public pack.
- Extended manifests, if needed, should live under this directory and should write reports to `bench/reports/extended/`, `bench/reports/extended-sample/`, or a temporary local directory.
- Regenerate B1 splits with `python scripts/build_extended_pack.py`; validate them with `make extended-pack-check`.
- Evaluation splits cover all 20 source families once and then fill with dispatchable families, keeping expected manual review rate inside the submission gate.
- `expected_ticket.json` is allowed in `public_train` only as a training/contract label. Multimodal `public_dev`, `public_test_frozen`, and `private_holdout` cases must remain sidecar-free and are guarded by `make leakage-guard`.
