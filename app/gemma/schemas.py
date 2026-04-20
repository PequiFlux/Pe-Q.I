"""
    O schema é uma parte fundamental do desenvolvimento de APIs, pois define a estrutura dos dados que serão enviados e recebidos pela API.

 pydantic: é utilizado para validar os dados de entrada e saída da API, garantindo que eles estejam no 
 formato correto e atendam aos requisitos definidos. Ele também facilita a criação de modelos de dados e a 
 documentação automática da API.

 BaseModel: é a classe base do pydantic, que é usada para criar modelos de dados personalizados. Ela fornece uma série de funcionalidades, 
 como validação de dados, conversão de tipos e geração de documentação.

Field: é uma função do pydantic que é usada para definir os campos de um modelo de dados. Ele permite especificar o tipo de dado, valores padrão, validações adicionais 
e outras opções para cada campo.

typing: é um módulo do Python que fornece suporte para anotações de tipo. Ele é usado para indicar os tipos de dados esperados para variáveis, 
funções e outros elementos do código.

List: é um tipo de dado do módulo typing que representa uma lista de elementos. 
Ele é usado para indicar que um campo em um modelo de dados deve ser uma lista de um determinado tipo.

Optional: é um tipo de dado do módulo typing que indica que um campo em um modelo de dados é opcional, 
ou seja, pode ser omitido ou ter um valor nulo. Ele é usado para indicar que um campo não é obrigatório e pode ser deixado em branco.  
 """
from pydantic import BaseModel, Field 
from typing import List, Optional, Literal

# 1. O que a IA extrai do PAPEL (Ticket)
class ParsedTicket(BaseModel):
    ticket_id: str = Field(..., description="ID do ticket (ex: TCK-001)")
    truck_id: Optional[str] = Field(None, description="Placa do caminhão (ex: TRK-001)")
    vehicle_type: str = Field(..., description="Tipo do veículo (ex: bitrem, truck)")
    
    # Status documental crítico para a decisão
    document_status: Literal["clear", "blocked", "incomplete", "unknown"] = Field(...)
    document_block_flags: List[str] = Field(default=[], description="Motivos de bloqueio explícitos")
    
    # Condição da carga para regras de moega
    load_condition: Literal["dry", "wet", "unknown"] = Field(...)
    contract_priority_flag: bool = Field(default=False)
    destination_constraints: Optional[str] = Field(None)

    # Metadados de qualidade do processo
    parse_confidence: float = Field(..., ge=0, le=1, description="Confiança da IA (0 a 1)")
    ambiguities: List[str] = Field(default=[], description="Dúvidas ou dados ilegíveis")
    evidence_refs: List[str] = Field(default=[], description="Trechos do texto que provam os dados")


# 2. O que a IA interpreta da NOTA DO OPERADOR
class ExceptionAssessment(BaseModel):
    primary_exception: Optional[str] = Field(None, description="A irregularidade principal identificada")
    severity: Literal["low", "medium", "high", "none"] = "none"
    affected_resources: List[str] = Field(default=[], description="IDs de moegas ou silos afetados")
    needs_human_review: bool = Field(default=False, description="IA sugere revisão manual?")


# 3. O "Pacote Final" que você entrega ao sistema
class InterpretedContext(BaseModel):
    parsed_ticket: ParsedTicket
    exception_assessment: ExceptionAssessment
    is_review_required: bool = Field(default=False, description="Sinalizador final de segurança")
    # proveniência: rastreia se a info veio do ticket ou da nota
    provenance_summary: str = Field(..., description="Breve resumo de onde os dados vieram")