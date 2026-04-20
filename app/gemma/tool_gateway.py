from typing import Dict, Any, Callable

class ToolGateway:
    """
    Gerencia as funções que a IA pode chamar (Function Calling).
    Atua como o portal entre o Gemma e o resto do sistema PequiFlux.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """Registra uma nova função que a IA poderá usar."""
        self.tools[name] = func

    def execute_tool(self, name: str, **kwargs) -> Any:
        """Executa a ferramenta solicitada pela IA."""
        if name not in self.tools:
            raise ValueError(f"Ferramenta {name} não encontrada no Gateway.")
        return self.tools[name](**kwargs)