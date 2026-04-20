class GemmaError(Exception):
    """Classe base para erros no módulo Gemma."""
    pass

class GemmaParseError(GemmaError):
    """Erro quando a IA devolve um JSON inválido ou campos faltando."""
    pass

class GemmaAPIError(GemmaError):
    """Erro de comunicação com o servidor do Google (timeout ou chave inválida)."""
    pass

class GemmaSafetyError(GemmaError):
    """Erro disparado quando o filtro de segurança da IA bloqueia a resposta."""
    pass