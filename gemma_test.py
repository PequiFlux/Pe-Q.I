from app.gemma import GemmaAdapter # Importando o adapter que criamos para o modelo Gemma
import os # Para lidar com caminhos de arquivos de forma mais segura
from dotenv import load_dotenv # Para carregar as variáveis de ambiente do arquivo .env

# 1. Configuração 
load_dotenv() # Carrega as variáveis de ambiente do arquivo .env
CHAVE_API = os.getenv("GEMINI_API_KEY")
adapter = GemmaAdapter(api_key=CHAVE_API)

# 2. Dados de Entrada (Simulando o que viria da Portaria)
imagem = os.path.join("data", "tickets", "ticket_teste.pdf")
nota_operador = "O motorista relatou que pegou chuva na estrada."
clima_api = "Precipitação: Moderada"

print("--- Iniciando Interpretação da Portaria ---")

try:
    # 3. Chamando a sua IA
    resultado = adapter.parse_ticket_document(
        file_path=imagem,
        operator_note=nota_operador,
        weather_state=clima_api
    )

    # 4. Verificando o resultado
    print(f"ID do Ticket: {resultado.parsed_ticket.ticket_id}")
    print(f"Condição da Carga: {resultado.parsed_ticket.load_condition}")
    print(f"Precisa de Revisão? {'SIM' if resultado.is_review_required else 'NÃO'}")
    print(f"Resumo da IA: {resultado.provenance_summary}")

except Exception as e:
    print(f"O teste falhou, mas o sistema capturou o erro: {e}")