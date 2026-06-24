import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env se ele existir
load_dotenv()

# Caminhos do projeto
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documentos"
OUTPUT_DIR = BASE_DIR / "saida"

# Garante que os diretórios existam
DOCS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Chave da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurações padrão do pregão (podem ser sobrescritas via CLI/argumentos)
DEFAULT_UASG = "120001"
DEFAULT_NUM_COMPRA = "05/2026"
DEFAULT_OBJETO = "Aquisição de computadores portáteis e periféricos para a Administração Pública"
