from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import (
    DecisionStatus,
    DocumentStatus,
    LoadCondition,
    OperatorAction,
    Severity,
    SourceKind,
    VehicleType,
)

DecisionVariant = Literal["fifo", "heuristic", "full"]
RunMode = Literal["interactive", "benchmark"]
TicketContentType = Literal["application/pdf", "image/png", "image/jpeg", "text/plain"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class WeatherState(StrictModel):
    precipitation: str
    severity: str
    timestamp: datetime | None = None


class ResourceState(StrictModel):
    resource_id: str
    status: str
    capacity_pct: float
    resource_type: str | None = None
    exposure: str
    allowed_vehicle_types: list[VehicleType] = Field(default_factory=list)
    supported_load_conditions: list[LoadCondition] = Field(
        default_factory=lambda: [LoadCondition.DRY]
    )


class RawQueueRow(StrictModel):
    truck_id: str
    arrival_ts: datetime
    status: str = "waiting"
    vehicle_type: VehicleType = VehicleType.UNKNOWN
    contract_priority_flag: bool = False


class QueueRow(RawQueueRow):
    queue_position: int
    wait_minutes: int


class QueueSnapshot(StrictModel):
    request_id: str
    rows: list[QueueRow]
    snapshot_at: datetime = Field(default_factory=utc_now)

    @computed_field
    @property
    def waiting_rows(self) -> list[QueueRow]:
        return [row for row in self.rows if row.status.lower() == "waiting"]


class DecisionRequest(StrictModel):
    request_id: str
    scenario_id: str
    variant: DecisionVariant
    queue_csv_ref: str
    ticket_ref: str
    ticket_content_type: TicketContentType
    operator_note: str
    weather_state: WeatherState
    resource_state: list[ResourceState]
    policy_profile_version: str
    run_mode: RunMode
    received_at: datetime = Field(default_factory=utc_now)

    @computed_field
    @property
    def candidate_destinations(self) -> list[str]:
        return [resource.resource_id for resource in self.resource_state]


class DocumentBundle(StrictModel):
    request_id: str
    document_ref: str
    content_type: TicketContentType
    sha256: str
    extracted_text: str | None = None
    rendered_pages: list[str] = Field(default_factory=list)
    candidate_truck_ids: list[str] = Field(default_factory=list)


class ParsedTicket(StrictModel):
    ticket_id: str | None = None
    truck_id: str | None = None
    vehicle_type: VehicleType = VehicleType.UNKNOWN
    document_status: DocumentStatus = DocumentStatus.UNKNOWN
    document_block_flags: list[str] = Field(default_factory=list)
    load_condition: LoadCondition = LoadCondition.UNKNOWN
    contract_priority_flag: bool = False
    destination_constraints: list[str] = Field(default_factory=list)
    parse_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ExceptionAssessment(StrictModel):
    primary_exception: str
    secondary_exceptions: list[str] = Field(default_factory=list)
    severity: Severity
    affected_resources: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    needs_human_review: bool = False


class TruthResolution(StrictModel):
    authoritative_sources: list[str]
    material_conflicts: list[str] = Field(default_factory=list)


class ProvenanceRecord(StrictModel):
    field: str
    source: SourceKind
    confidence: float | None = None


class InterpretedContext(StrictModel):
    parsed_ticket: ParsedTicket
    exception_assessment: ExceptionAssessment
    truth_resolution: TruthResolution
    provenance: list[ProvenanceRecord]
    needs_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)


class ConstraintFailure(StrictModel):
    constraint_id: str
    severity: str
    source: str
    detail: str


class ValidationEntry(StrictModel):
    truck_id: str
    destination_id: str
    eligible: bool
    failed_constraints: list[ConstraintFailure] = Field(default_factory=list)


class ValidationResult(StrictModel):
    validation_matrix: list[ValidationEntry]
    global_blocks: list[str] = Field(default_factory=list)
    policy_profile_version: str
    validated_at: datetime = Field(default_factory=utc_now)


class RankedCandidate(StrictModel):
    truck_id: str
    destination_id: str
    score: float
    queue_position: int
    arrival_ts: datetime
    fired_rules: list[str] = Field(default_factory=list)
    fifo_break: bool = False
    reason_details: list[str] = Field(default_factory=list)


class RankedCandidates(StrictModel):
    candidates: list[RankedCandidate]
    decided_at: datetime = Field(default_factory=utc_now)

    @property
    def top_candidate(self) -> RankedCandidate | None:
        return self.candidates[0] if self.candidates else None


class RecommendedTruck(StrictModel):
    truck_id: str
    queue_position_before: int
    queue_position_after: int


class RecommendedDestination(StrictModel):
    destination_id: str
    destination_type: str


class QueueDiffEntry(StrictModel):
    truck_id: str
    position_before: int
    position_after: int | None
    decision: str
    reason: str


class DriverMessage(StrictModel):
    message: str
    template_id: str


class DecisionPreview(StrictModel):
    decision_id: str
    request_id: str
    scenario_id: str
    variant: DecisionVariant
    decision_status: DecisionStatus
    recommended_truck: RecommendedTruck | None = None
    recommended_destination: RecommendedDestination | None = None
    considered_constraints: list[ConstraintFailure] = Field(default_factory=list)
    reason_summary: str
    reason_details: list[str] = Field(default_factory=list)
    operator_actions: list[OperatorAction] = Field(default_factory=list)
    queue_diff: list[QueueDiffEntry] = Field(default_factory=list)
    fired_rules: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class OperatorDecision(StrictModel):
    action_type: OperatorAction
    reason: str
    actor_id: str
    requested_truck_id: str | None = None
    requested_destination_id: str | None = None


class DecisionFinalized(StrictModel):
    decision_id: str
    final_status: DecisionStatus
    operator_action: OperatorDecision
    finalized_at: datetime = Field(default_factory=utc_now)


class AuditRecord(StrictModel):
    decision_id: str
    request_id: str
    scenario_id: str
    variant: DecisionVariant
    hard_constraints_checked: list[dict[str, Any]] = Field(default_factory=list)
    fired_rules: list[str] = Field(default_factory=list)
    rejected_candidates: list[dict[str, Any]] = Field(default_factory=list)
    recommended_pair: dict[str, Any] | None = None
    fifo_break: bool = False
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    operator_action: dict[str, Any] | None = None
    latencies_ms: dict[str, int] = Field(default_factory=dict)
    source_hashes: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class GemmaVisibleSummary(StrictModel):
    parsed_fields: list[str] = Field(default_factory=list)
    exception_label: str
    notes: list[str] = Field(default_factory=list)


class FrontEndPayload(StrictModel):
    request_id: str
    scenario_id: str
    variant: DecisionVariant
    decision_status: DecisionStatus
    recommended_truck: RecommendedTruck | None = None
    recommended_destination: RecommendedDestination | None = None
    considered_constraints: list[ConstraintFailure] = Field(default_factory=list)
    reason_summary: str
    reason_details: list[str] = Field(default_factory=list)
    driver_message: DriverMessage
    operator_actions: list[OperatorAction] = Field(default_factory=list)
    queue_diff: list[QueueDiffEntry] = Field(default_factory=list)
    gemma_visible_summary: GemmaVisibleSummary
    latency_ms: dict[str, int] = Field(default_factory=dict)
    benchmark_tags: list[str] = Field(default_factory=list)
    benchmark_observed: dict[str, Any] = Field(default_factory=dict)
    confidence_notes: list[str] = Field(default_factory=list)
    audit_record: AuditRecord | None = None


class PolicyWeights(StrictModel):
    fifo_position: int = 40
    contract_priority: int = 30
    resource_fit: int = 15
    capacity_headroom: int = 10
    wait_sla_pressure: int = 5


class PolicyProfile(StrictModel):
    version: str
    min_operational_capacity_pct: int
    comfort_capacity_pct: int
    weights: PolicyWeights
    tie_breakers: list[str]
