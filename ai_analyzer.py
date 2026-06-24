import json
import time
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from config import GEMINI_API_KEY

# Define o modelo padrão da API do Gemini como fallback
DEFAULT_MODEL_NAME = "gemini-2.0-flash"

# =====================================================================
# Modelos Pydantic para Saídas Estruturadas
# =====================================================================

class TRItem(BaseModel):
    item_num: str = Field(description="Número do item ou lote no Termo de Referência (ex: '1', '2', 'Lote 1')")
    nome: str = Field(description="Nome resumido do produto ou serviço")
    especificacao: str = Field(description="Especificação técnica detalhada/exigências mínimas do item")

class TRDados(BaseModel):
    itens: List[TRItem] = Field(description="Lista de todos os itens e especificações técnicas exigidas no Termo de Referência")

class ProposalItem(BaseModel):
    item_num_correspondente: Optional[str] = Field(None, description="Número do item correspondente do TR que este item visa atender")
    descricao: str = Field(description="Descrição detalhada do item ofertado pelo fornecedor")
    marca: Optional[str] = Field(None, description="Marca do produto ofertado (se informada)")
    modelo: Optional[str] = Field(None, description="Modelo do produto ofertado (se informado)")
    valor_unitario: Optional[float] = Field(None, description="Valor unitário ofertado")
    valor_total: Optional[float] = Field(None, description="Valor total do item ofertado")

class SupplierProposal(BaseModel):
    razao_social: str = Field(description="Razão Social completa da empresa fornecedora")
    cnpj: str = Field(description="CNPJ da empresa fornecedora no formato XX.XXX.XXX/XXXX-XX ou apenas dígitos")
    itens: List[ProposalItem] = Field(description="Lista de itens ofertados na proposta comercial")

class ConfrontoItem(BaseModel):
    item_num: str = Field(description="Número do item correspondente no TR")
    confronto_ia: str = Field(description="Análise detalhada comparando a especificação exigida no TR com o item ofertado na proposta. Indique claramente se atende ou não atende a cada requisito essencial.")
    status_sugerido: str = Field(description="Status sugerido para o item. Escolha obrigatória entre: 'Aceito', 'Não aceito', 'Pendência'")


# Decorador para tratamento de Rate Limits (429) e Sobrecargas Temporárias (503)
def retry_on_rate_limit(max_retries=5, initial_delay=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e).lower()
                    is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str
                    is_unavailable = "503" in err_str or "unavailable" in err_str or "demand" in err_str
                    
                    if is_rate_limit or is_unavailable:
                        wait_time = delay
                        if "retry in" in err_str:
                            try:
                                parts = err_str.split("retry in")
                                if len(parts) > 1:
                                    sec_str = parts[1].strip().split("s")[0].strip()
                                    wait_time = float(sec_str) + 3.0
                            except Exception:
                                pass
                        
                        print(f"⚠️ [API Gemini] Rate Limit ou Sobrecarga. Aguardando {wait_time:.1f}s antes da tentativa {attempt + 1}/{max_retries}...")
                        try:
                            import streamlit as st
                            st.warning(f"⚠️ Limite da API do Gemini atingido. Aguardando {wait_time:.0f}s para prosseguir de forma segura...")
                        except Exception:
                            pass
                        
                        time.sleep(wait_time)
                        delay *= 2
                    else:
                        raise e
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =====================================================================
# Classe de Análise por Inteligência Artificial
# =====================================================================

class AIAnalyzer:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        if not GEMINI_API_KEY:
            raise ValueError(
                "A chave GEMINI_API_KEY não foi encontrada. "
                "Crie um arquivo .env na raiz do projeto contendo: GEMINI_API_KEY=sua_chave_aqui"
            )
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = model_name

    def _obter_conteudo_input(self, pdf_path: Path, ext_result: dict) -> list:
        """
        Retorna o conteúdo apropriado para a API do Gemini.
        Se o PDF for escaneado, envia os bytes do arquivo para processamento multimodal (OCR em nuvem).
        Caso contrário, envia o texto extraído localmente para otimização de tokens e velocidade.
        """
        if ext_result["is_scanned"]:
            print(f"  [IA] PDF '{pdf_path.name}' identificado como escaneado. Utilizando processamento multimodal (OCR de Imagem)...")
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            return [
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type="application/pdf"
                )
            ]
        else:
            print(f"  [IA] PDF '{pdf_path.name}' contém texto nativo. Enviando texto extraído...")
            return [f"Texto extraído do documento PDF:\n\n{ext_result['text']}"]

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def extrair_termos_de_referencia(self, pdf_path: Path, ext_result: dict) -> TRDados:
        """
        Analisa o PDF do Termo de Referência e extrai os itens exigidos estruturalmente.
        """
        print(f"[Processamento TR] Iniciando extração com IA de: {pdf_path.name}")
        conteudo = self._obter_conteudo_input(pdf_path, ext_result)
        
        prompt = (
            "Você é um Arquiteto de Soluções de TI e Especialista em Licitações Públicas. "
            "Sua tarefa é analisar o Termo de Referência (TR) anexado e identificar todos os itens que estão sendo licitados. "
            "Para cada item, extraia o número do item/lote, o nome descritivo do item e a sua especificação técnica detalhada "
            "(requisitos mínimos exigidos, como processador, memória, dimensões, certificações, etc.). "
            "Extraia as informações de forma rigorosa e fiel ao texto original."
        )
        
        conteudo.append(prompt)
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=conteudo,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TRDados,
                temperature=0.1
            )
        )
        
        # O retorno é parseado conforme o schema Pydantic TRDados
        return TRDados.model_validate_json(response.text)

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def extrair_proposta(self, pdf_path: Path, ext_result: dict) -> SupplierProposal:
        """
        Analisa o PDF da Proposta Comercial e extrai os dados do fornecedor e itens ofertados.
        """
        print(f"[Processamento Proposta] Iniciando extração com IA de: {pdf_path.name}")
        conteudo = self._obter_conteudo_input(pdf_path, ext_result)
        
        prompt = (
            "Você é um analista de licitações experiente. "
            "Analise a proposta comercial fornecida e extraia:\n"
            "1. A Razão Social completa do fornecedor;\n"
            "2. O CNPJ do fornecedor;\n"
            "3. Todos os itens ofertados pela empresa, contendo descrição detalhada do produto/serviço, "
            "marca, modelo, valor unitário e valor total. "
            "Caso a proposta mencione a correspondência com o número do item/lote do Termo de Referência, "
            "preencha o campo 'item_num_correspondente'. Se não for mencionado, tente inferir a partir do contexto."
        )
        
        conteudo.append(prompt)
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=conteudo,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SupplierProposal,
                temperature=0.1
            )
        )
        
        return SupplierProposal.model_validate_json(response.text)

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def confrontar_proposta_com_tr(self, tr_itens: List[TRItem], proposta_itens: List[ProposalItem]) -> List[ConfrontoItem]:
        """
        Compara os itens ofertados na proposta com os itens exigidos no Termo de Referência (TR).
        """
        print("[Confronto Técnico] Analisando conformidade com a LLM...")
        
        # Converte os dados estruturados para formato textual de fácil leitura para a LLM
        tr_text = "\n".join([
            f"- ITEM {item.item_num} ({item.nome}):\n  Especificações Exigidas: {item.especificacao}"
            for item in tr_itens
        ])
        
        prop_text = "\n".join([
            f"- ITEM {item.item_num_correspondente or 'Não especificado'} ({item.descricao}):\n  Ofertado: Marca {item.marca or 'N/A'}, Modelo {item.modelo or 'N/A'}, Valor: R$ {item.valor_unitario or 0:.2f}"
            for item in proposta_itens
        ])
        
        prompt = (
            "Você é um Arquiteto de TI e Analista Técnico de Licitações. "
            "Sua função é confrontar os itens ofertados na Proposta Comercial com os requisitos mínimos exigidos "
            "no Termo de Referência (TR).\n\n"
            "Abaixo estão as exigências técnicas do Termo de Referência (TR):\n"
            f"{tr_text}\n\n"
            "Abaixo estão os itens ofertados pela Proposta Comercial do Fornecedor:\n"
            f"{prop_text}\n\n"
            "Para cada item da Proposta, compare-o com o respectivo item exigido no TR. "
            "Gere uma análise técnica detalhada comparando as especificações exigidas vs. ofertadas. "
            "Identifique qualquer desconformidade, omissão de recurso ou divergência em relação ao solicitado. "
            "Retorne o resultado de forma estruturada. No campo 'status_sugerido', indique:\n"
            "- 'Aceito': se atender a todas as exigências ou for superior.\n"
            "- 'Não aceito': se houver divergência evidente de especificações essenciais (ex: processador inferior, falta de itens obrigatórios).\n"
            "- 'Pendência': se faltarem detalhes cruciais na descrição da proposta que impeçam a avaliação (ex: não citar a marca/modelo de forma clara, ou omitir velocidade de processamento)."
        )
        
        class ConfrontoResponse(BaseModel):
            confrontos: List[ConfrontoItem]
            
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ConfrontoResponse,
                temperature=0.1
            )
        )
        
        parsed_res = ConfrontoResponse.model_validate_json(response.text)
        return parsed_res.confrontos
