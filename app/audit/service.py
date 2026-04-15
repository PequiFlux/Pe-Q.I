from __future__ import annotations

from app.audit.payloads import build_audit_record
from app.domain.models import AuditRecord, DecisionPreview, InterpretedContext, ValidationResult


class AuditService:
    def generate_audit_payload(
        self,
        *,
        interpreted_context: InterpretedContext,
        validation: ValidationResult | None,
        preview: DecisionPreview,
        latencies_ms: dict[str, int],
        source_hashes: dict[str, str],
        operator_action: dict | None = None,
    ) -> AuditRecord:
        return build_audit_record(
            preview=preview,
            interpreted_context=interpreted_context,
            validation=validation,
            latencies_ms=latencies_ms,
            source_hashes=source_hashes,
            operator_action=operator_action,
        )

