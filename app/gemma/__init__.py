from .adapter import GemmaAdapter
from .schemas import InterpretedContext, ParsedTicket
from .fallback import get_fallback_context
from .exceptions import GemmaError, GemmaParseError

# Isso define o que será exportado quando alguém der 'from app.gemma import *'
__all__ = [
    "GemmaAdapter",
    "InterpretedContext",
    "ParsedTicket",
    "get_fallback_context",
    "GemmaError",
    "GemmaParseError"
]