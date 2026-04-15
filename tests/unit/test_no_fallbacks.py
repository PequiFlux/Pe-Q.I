from __future__ import annotations

import pytest

from app.domain.errors import FallbackForbiddenError
from app.gemma.fallback import forbid_fallback


def test_fallbacks_are_forbidden() -> None:
    with pytest.raises(FallbackForbiddenError):
        forbid_fallback()
