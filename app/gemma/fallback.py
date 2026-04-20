from .schemas import InterpretedContext, ParsedTicket, ExceptionAssessment

def get_fallback_context(error_message: str) -> InterpretedContext:
    """
    Gera um contexto de segurança caso a IA falhe. 
    Bloqueia o despacho automático e solicita revisão humana.
    """
    
    fallback_ticket = ParsedTicket(
        ticket_id="FALLBACK-PENDING",
        truck_id=None,
        vehicle_type="unknown",
        document_status="unknown",
        load_condition="unknown",
        parse_confidence=0.0,
        ambiguities=["IA Indisponível: " + error_message]
    )
    
    fallback_exception = ExceptionAssessment(
        primary_exception="Erro no Processamento da IA",
        severity="high",
        needs_human_review=True
    )
    
    return InterpretedContext(
        parsed_ticket=fallback_ticket,
        exception_assessment=fallback_exception,
        is_review_required=True,
        provenance_summary="Fallback gerado por erro no módulo Gemma."
    )