import pdfplumber
from pathlib import Path
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: Path) -> dict:
    """
    Tenta extrair o texto de um PDF de forma local.
    Retorna um dicionário contendo:
      - 'text': O texto extraído (ou string vazia).
      - 'is_scanned': True se não houver texto extraível (sugerindo PDF escaneado/imagem).
      - 'num_pages': Número total de páginas.
    """
    pdf_path = Path(pdf_path)
    result = {
        "text": "",
        "is_scanned": False,
        "num_pages": 0
    }
    
    try:
        reader = PdfReader(pdf_path)
        result["num_pages"] = len(reader.pages)
        
        # Tenta extrair com pdfplumber para obter melhor qualidade estrutural de tabelas/linhas
        full_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
        
        extracted_text = "\n".join(full_text).strip()
        result["text"] = extracted_text
        
        # Se o texto for muito curto comparado ao número de páginas, assumimos que é escaneado
        # Regra de corte: menos de 100 caracteres por página de média
        if len(extracted_text) < (100 * result["num_pages"]):
            result["is_scanned"] = True
            
    except Exception as e:
        print(f"Erro na extração local do PDF {pdf_path.name}: {e}")
        result["is_scanned"] = True
        
    return result
