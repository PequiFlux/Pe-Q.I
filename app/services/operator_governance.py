from __future__ import annotations

from app.domain.constraints import validate_override_action
from app.domain.enums import DecisionStatus, OperatorAction
from app.domain.errors import PequiFluxError
from app.domain.models import (
    AuditRecord,
    DecisionFinalized,
    FrontEndPayload,
    OperatorDecision,
    ValidationEntry,
    ValidationResult,
)
from app.storage.sqlite_store import SQLiteStore


def finalize_operator_decision(
    *,
    payload: FrontEndPayload,
    action_type: OperatorAction | str,
    reason: str,
    actor_id: str,
    requested_truck_id: str | None = None,
    requested_destination_id: str | None = None,
    sqlite_store: SQLiteStore | None = None,
) -> tuple[DecisionFinalized, AuditRecord]:
    audit = payload.audit_record
    if audit is None:
        raise PequiFluxError("AUDIT_RECORD_REQUIRED", "Operator finalization requires an audit record.")

    action = OperatorDecision(
        action_type=OperatorAction(action_type),
        reason=reason,
        actor_id=actor_id,
        requested_truck_id=requested_truck_id,
        requested_destination_id=requested_destination_id,
    )
    _validate_action(payload=payload, action=action)

    finalized = DecisionFinalized(
        decision_id=audit.decision_id,
        final_status=_final_status(action.action_type),
        operator_action=action,
    )
    updated_audit = audit.model_copy(
        update={
            "operator_action": {
                **action.model_dump(mode="json"),
                "final_status": finalized.final_status,
                "finalized_at": finalized.finalized_at.isoformat(),
            }
        }
    )

    if sqlite_store is not None:
        sqlite_store.initialize()
        sqlite_store.save_operator_action(finalized.decision_id, action)
        sqlite_store.save_decision_finalized(finalized)
        sqlite_store.save_audit_record(updated_audit)

    return finalized, updated_audit


def _validate_action(*, payload: FrontEndPayload, action: OperatorDecision) -> None:
    if not action.reason.strip():
        raise PequiFluxError("OPERATOR_REASON_REQUIRED", "Operator action requires an explicit reason.")

    if action.action_type == OperatorAction.APPROVE:
        if payload.decision_status != DecisionStatus.PREVIEW_READY:
            raise PequiFluxError("APPROVAL_REQUIRES_PREVIEW", "Approve requires a preview-ready decision.")
        if payload.recommended_truck is None or payload.recommended_destination is None:
            raise PequiFluxError("APPROVAL_TARGET_REQUIRED", "Approve requires a recommended pair.")
        return

    if action.action_type == OperatorAction.BLOCK:
        return

    if action.action_type == OperatorAction.OVERRIDE:
        validation = _validation_from_audit(payload)
        validate_override_action(validation=validation, operator_action=action)
        return

    raise PequiFluxError("UNSUPPORTED_OPERATOR_ACTION", f"Unsupported operator action: {action.action_type}")


def _validation_from_audit(payload: FrontEndPayload) -> ValidationResult:
    audit = payload.audit_record
    if audit is None or not audit.hard_constraints_checked:
        raise PequiFluxError(
            "VALIDATION_MATRIX_REQUIRED",
            "Override requires a persisted validation matrix.",
        )
    return ValidationResult(
        validation_matrix=[
            ValidationEntry.model_validate(entry) for entry in audit.hard_constraints_checked
        ],
        policy_profile_version="from-audit",
    )


def _final_status(action_type: OperatorAction) -> DecisionStatus:
    if action_type == OperatorAction.APPROVE:
        return DecisionStatus.APPROVED
    if action_type == OperatorAction.BLOCK:
        return DecisionStatus.BLOCKED
    if action_type == OperatorAction.OVERRIDE:
        return DecisionStatus.OVERRIDDEN
    raise PequiFluxError("UNSUPPORTED_OPERATOR_ACTION", f"Unsupported operator action: {action_type}")
