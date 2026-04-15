from __future__ import annotations

from app.domain.models import AuditRecord, DecisionPreview, InterpretedContext, ValidationResult


def build_audit_record(
    *,
    preview: DecisionPreview,
    interpreted_context: InterpretedContext,
    validation: ValidationResult | None,
    latencies_ms: dict[str, int],
    source_hashes: dict[str, str],
    operator_action: dict | None = None,
) -> AuditRecord:
    rejected = []
    checked = []
    if validation is not None:
        checked = [entry.model_dump(mode="json") for entry in validation.validation_matrix]
        rejected = [
            entry.model_dump(mode="json")
            for entry in validation.validation_matrix
            if not entry.eligible
        ]

    recommended_pair = None
    if preview.recommended_truck and preview.recommended_destination:
        recommended_pair = {
            "truck_id": preview.recommended_truck.truck_id,
            "destination_id": preview.recommended_destination.destination_id,
        }

    return AuditRecord(
        decision_id=preview.decision_id,
        request_id=preview.request_id,
        scenario_id=preview.scenario_id,
        variant=preview.variant,
        hard_constraints_checked=checked,
        fired_rules=preview.fired_rules,
        rejected_candidates=rejected,
        recommended_pair=recommended_pair,
        fifo_break=bool(preview.recommended_truck and preview.recommended_truck.queue_position_before != 1),
        provenance=[item.model_dump(mode="json") for item in interpreted_context.provenance],
        operator_action=operator_action,
        latencies_ms=latencies_ms,
        source_hashes=source_hashes,
    )

