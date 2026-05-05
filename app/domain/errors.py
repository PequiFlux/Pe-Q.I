from __future__ import annotations


class PequiFluxError(Exception):
    """Base formal error used across the modular monolith."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SchemaViolationError(PequiFluxError):
    def __init__(self, message: str) -> None:
        super().__init__("SCHEMA_VIOLATION", message)


class ReviewRequiredError(PequiFluxError):
    def __init__(self, message: str) -> None:
        super().__init__("REVIEW_REQUIRED", message)


class FallbackForbiddenError(PequiFluxError):
    def __init__(self) -> None:
        super().__init__(
            "FALLBACK_FORBIDDEN",
            "Fallback behavior is forbidden by repository policy.",
        )
