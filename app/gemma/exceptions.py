from __future__ import annotations

from app.domain.errors import PequiFluxError


class GemmaError(PequiFluxError):
    """Base formal error for Gemma integration failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)


class GemmaParseError(GemmaError):
    def __init__(self, message: str = "Gemma returned invalid structured output.") -> None:
        super().__init__("GEMMA_PARSE_ERROR", message)


class GemmaAPIError(GemmaError):
    def __init__(self, message: str = "Gemma runtime API failed.") -> None:
        super().__init__("GEMMA_API_ERROR", message)


class GemmaSafetyError(GemmaError):
    def __init__(self, message: str = "Gemma safety policy blocked the response.") -> None:
        super().__init__("GEMMA_SAFETY_ERROR", message)
