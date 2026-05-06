from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError


JsonSchema = dict[str, Any]

TOOL_STATE_ORDER: dict[str, set[str]] = {
    "validate_hard_constraints": {FlowState.INTERPRETED.value},
    "rank_candidates": {FlowState.VALIDATED.value},
    "generate_audit_payload": {
        FlowState.RANKED.value,
        FlowState.REVIEW_REQUIRED.value,
    },
}


def available_tools_for_state(state: FlowState | str) -> list[str]:
    state_value = _state_value(state)
    return [
        tool_name
        for tool_name, allowed_states in TOOL_STATE_ORDER.items()
        if state_value in allowed_states
    ]


@dataclass(frozen=True)
class ToolLocalIds:
    truck_ids: set[str] = field(default_factory=set)
    destination_ids: set[str] = field(default_factory=set)
    request_ids: set[str] = field(default_factory=set)

    @classmethod
    def from_iterables(
        cls,
        *,
        truck_ids: list[str] | set[str] | None = None,
        destination_ids: list[str] | set[str] | None = None,
        request_ids: list[str] | set[str] | None = None,
    ) -> "ToolLocalIds":
        return cls(
            truck_ids=set(truck_ids or []),
            destination_ids=set(destination_ids or []),
            request_ids=set(request_ids or []),
        )


class ToolGateway:
    """Whitelisted execution gateway for model-issued tool intents."""

    def __init__(
        self,
        tools: dict[str, Callable[..., Any]],
        *,
        tool_schemas: dict[str, JsonSchema] | None = None,
        current_state: FlowState | str | None = None,
        local_ids: ToolLocalIds | None = None,
        logger: Any | None = None,
    ) -> None:
        self._tools = dict(tools)
        self._tool_schemas = dict(tool_schemas or {})
        self._current_state = _state_value(current_state) if current_state is not None else None
        self._local_ids = local_ids or ToolLocalIds()
        self._logger = logger

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        request_id = arguments.get("request_id") if isinstance(arguments, dict) else None
        self._log_attempt(tool_name=tool_name, status="attempted", request_id=request_id)
        try:
            if tool_name not in self._tools:
                raise PequiFluxError("UNKNOWN_TOOL", f"Tool not allowed: {tool_name}")
            if not isinstance(arguments, dict):
                raise PequiFluxError("SCHEMA_ERROR", "Tool arguments must be an object.")
            self._validate_tool_order(tool_name)
            self._validate_schema(tool_name, arguments)
            self._validate_local_ids(arguments)
            result = self._tools[tool_name](**arguments)
        except PequiFluxError as exc:
            self._log_attempt(
                tool_name=tool_name,
                status="error",
                request_id=request_id,
                error_code=exc.code,
            )
            raise
        except TimeoutError as exc:
            self._log_attempt(
                tool_name=tool_name,
                status="error",
                request_id=request_id,
                error_code="TIMEOUT",
            )
            raise PequiFluxError("TIMEOUT", f"Tool timed out: {tool_name}") from exc
        except Exception as exc:
            self._log_attempt(
                tool_name=tool_name,
                status="error",
                request_id=request_id,
                error_code="EXECUTION_ERROR",
            )
            raise PequiFluxError("EXECUTION_ERROR", f"Tool execution failed: {tool_name}") from exc

        self._log_attempt(tool_name=tool_name, status="executed", request_id=request_id)
        return result

    def _validate_tool_order(self, tool_name: str) -> None:
        if self._current_state is None:
            return
        allowed_states = TOOL_STATE_ORDER.get(tool_name)
        if allowed_states is None:
            return
        if self._current_state not in allowed_states:
            raise PequiFluxError(
                "TOOL_ORDER_ERROR",
                f"Tool {tool_name} is not allowed in state {self._current_state}.",
            )

    def _validate_schema(self, tool_name: str, arguments: dict[str, Any]) -> None:
        schema = self._tool_schemas.get(tool_name)
        if schema is None:
            return
        if schema.get("type") != "object":
            raise PequiFluxError(
                "SCHEMA_ERROR", f"Tool schema for {tool_name} must be an object schema."
            )

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        additional_allowed = bool(schema.get("additionalProperties", True))
        missing = sorted(required - set(arguments))
        if missing:
            raise PequiFluxError("SCHEMA_ERROR", f"Missing tool arguments: {', '.join(missing)}")
        if not additional_allowed:
            extra = sorted(set(arguments) - set(properties))
            if extra:
                raise PequiFluxError(
                    "SCHEMA_ERROR", f"Unexpected tool arguments: {', '.join(extra)}"
                )

        for key, value in arguments.items():
            if key in properties:
                _validate_value_schema(key, value, properties[key])

    def _validate_local_ids(self, arguments: dict[str, Any]) -> None:
        _validate_ids(
            value=arguments,
            truck_ids=self._local_ids.truck_ids,
            destination_ids=self._local_ids.destination_ids,
            request_ids=self._local_ids.request_ids,
        )

    def _log_attempt(
        self,
        *,
        tool_name: str,
        status: str,
        request_id: Any | None = None,
        error_code: str | None = None,
    ) -> None:
        if self._logger is None:
            return
        payload = {
            "module": "tool_gateway",
            "event_type": "tool_call_executed" if status == "executed" else "tool_call_attempted",
            "tool_name": tool_name,
            "status": status,
        }
        if request_id is not None:
            payload["request_id"] = str(request_id)
        if self._current_state is not None:
            payload["state"] = self._current_state
        if error_code is not None:
            payload["error_code"] = error_code
        self._logger.write(payload)


def _validate_value_schema(key: str, value: Any, schema: JsonSchema) -> None:
    expected_type = schema.get("type")
    if expected_type is None:
        return
    expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
    if not any(_matches_json_type(value, item) for item in expected_types):
        raise PequiFluxError("SCHEMA_ERROR", f"Tool argument {key} has invalid type.")
    if schema.get("enum") is not None and value not in schema["enum"]:
        raise PequiFluxError("SCHEMA_ERROR", f"Tool argument {key} is not an allowed enum value.")
    if isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < int(min_items):
            raise PequiFluxError("SCHEMA_ERROR", f"Tool argument {key} has too few items.")
        max_items = schema.get("maxItems")
        if max_items is not None and len(value) > int(max_items):
            raise PequiFluxError("SCHEMA_ERROR", f"Tool argument {key} has too many items.")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_value_schema(f"{key}[{index}]", item, item_schema)


def _matches_json_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int | float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    raise PequiFluxError("SCHEMA_ERROR", f"Unsupported JSON Schema type: {expected_type}")


def _validate_ids(
    *,
    value: Any,
    truck_ids: set[str],
    destination_ids: set[str],
    request_ids: set[str],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"truck_id", "requested_truck_id"} and truck_ids and item not in truck_ids:
                raise PequiFluxError("DOMAIN_VALIDATION_ERROR", f"Unknown truck_id: {item}")
            if (
                key in {"destination_id", "requested_destination_id"}
                and destination_ids
                and item not in destination_ids
            ):
                raise PequiFluxError("DOMAIN_VALIDATION_ERROR", f"Unknown destination_id: {item}")
            if key == "request_id" and request_ids and item not in request_ids:
                raise PequiFluxError("DOMAIN_VALIDATION_ERROR", f"Unknown request_id: {item}")
            _validate_ids(
                value=item,
                truck_ids=truck_ids,
                destination_ids=destination_ids,
                request_ids=request_ids,
            )
    elif isinstance(value, list):
        for item in value:
            _validate_ids(
                value=item,
                truck_ids=truck_ids,
                destination_ids=destination_ids,
                request_ids=request_ids,
            )


def _state_value(state: FlowState | str | None) -> str | None:
    if state is None:
        return None
    if isinstance(state, FlowState):
        return state.value
    return str(state)
