"""Adapter para comunicação com o modelo Gemma da Google, especializado em interpretação de tickets e notas operacionais."""
import google.generativeai as genai
import PIL.Image
import json
from .prompts import SYSTEM_INSTRUCTION, TICKET_EXTRACTION_PROMPT
from .schemas import InterpretedContext

class GemmaAdapter:
    def __init__(self, api_key: str):
        # 1. Autenticação e Configuração do Modelo
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )

    def parse_ticket_document(self, file_path: str, operator_note: str, weather_state: str) -> InterpretedContext:
        # 1. Verificar a extensão do ficheiro
        if file_path.lower().endswith('.pdf'):
            # Para PDF, fazemos o upload direto para a API do Google
            doc_file = genai.upload_file(path=file_path, mime_type="application/pdf")
            content_to_send = [TICKET_EXTRACTION_PROMPT.format(
                operator_note=operator_note,
                weather_state=weather_state
            ), doc_file]
        else:
            # Para imagens, mantemos o uso do PIL
            img = PIL.Image.open(file_path)
            content_to_send = [TICKET_EXTRACTION_PROMPT.format(
                operator_note=operator_note,
                weather_state=weather_state
            ), img]

        # 2. Enviar para a IA
        response = self.model.generate_content(content_to_send)
    

        # 5. Higienização e Validação (O "Pulo do Gato")
        # Removemos os backticks (```json) que a IA às vezes coloca por 'educação'
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        
        try:
            data = json.loads(raw_text)
            
            # Transformamos o JSON bruto na sua Ficha Oficial validada pelo Pydantic
            # Se faltar um campo obrigatório, o Pydantic avisará aqui!
            return InterpretedContext(**data)
            
        except Exception as e:
            # Se a IA 'alucinar' e não mandar um JSON válido, o sistema identifica o erro
            print(f"Erro na interpretação da portaria: {e}")
            raise ValueError("Falha crítica no contrato de dados do Gemma.")