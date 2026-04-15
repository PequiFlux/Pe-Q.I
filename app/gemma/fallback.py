from __future__ import annotations

from typing import NoReturn

from app.domain.errors import FallbackForbiddenError


def forbid_fallback() -> NoReturn:
    raise FallbackForbiddenError()

