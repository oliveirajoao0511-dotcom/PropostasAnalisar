import base64
import json
import time
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
import anthropic
from anthropic import RateLimitError, APIStatusError, APIError

from config import ANTHROPIC_API_KEY

# Define o modelo padrão da API do Claude
DEFAULT_MODEL_NAME = "claude-3-5-sonnet-20241022"

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

class ConfrontoResponse(BaseModel):
    confrontos: List[ConfrontoItem]


# Decorador para tratamento de Rate Limits (429) e Sobrecargas Temporárias (529) da Anthropic
def retry_on_rate_limit(max_retries=5, initial_delay=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e).lower()
                    # Anthropic usa 429 para rate limits e 529 para sobrecarga (overloaded)
                    is_rate_limit = isinstance(e, RateLimitError) or "429" in err_str or "rate limit" in err_str or "quota" in err_str
                    is_overloaded = "529" in err_str or "overloaded" in err_str or "overloaded_error" in err_str
                    
                    if is_rate_limit or is_overloaded:
                        wait_time = delay
                        # Se a mensagem contiver alguma instrução de tempo
                        if "retry in" in err_str or "try again in" in err_str:
                            try:
                                # Tenta extrair segundos aproximados
                                parts = err_str.replace("try again in", "retry in").split("retry in")
                                if len(parts) > 1:
                                    sec_str = parts[1].strip().split("s")[0].strip()
                                    wait_time = float(sec_str) + 3.0
                            except Exception:
                                pass
                        
                        print(f"⚠️ [API Anthropic] Rate Limit ou Sobrecarga (529). Aguardando {wait_time:.1f}s antes da tentativa {attempt + 1}/{max_retries}...")
                        try:
                            import streamlit as st
                            st.warning(f"⚠️ Limite da API da Anthropic atingido ou Servidor Sobregregado. Aguardando {wait_time:.0f}s para prosseguir de forma segura...")
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
# Classe de Análise por Inteligência Artificial (Claude)
# =====================================================================

class AIAnalyzer:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "A chave ANTHROPIC_API_KEY não foi encontrada. "
                "Crie um arquivo .env na raiz do projeto contendo: ANTHROPIC_API_KEY=sua_chave_aqui"
            )
        # Habilita o beta de leitura de PDF nativa do Claude 3.5
        self.client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            default_headers={"anthropic-beta": "pdfs-2024-09-25"}
        )
        self.model_name = model_name

    def _obter_conteudo_input(self, pdf_path: Path, ext_result: dict) -> list:
        """
        Retorna o conteúdo apropriado para a API da Anthropic.
        Se o PDF for escaneado, envia o arquivo codificado em base64 (OCR em nuvem da Anthropic).
        Caso contrário, envia o texto extraído localmente para economizar tokens e tempo.
        """
        if ext_result["is_scanned"]:
            print(f"  [IA] PDF '{pdf_path.name}' identificado como escaneado. Enviando PDF em base64 para processamento nativo do Claude...")
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                }
            ]
        else:
            print(f"  [IA] PDF '{pdf_path.name}' contém texto nativo. Enviando texto extraído...")
            return [
                {
                    "type": "text",
                    "text": f"Texto extraído do documento PDF:\n\n{ext_result['text']}"
                }
            ]

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def extrair_termos_de_referencia(self, pdf_path: Path, ext_result: dict) -> TRDados:
        """
        Analisa o PDF do Termo de Referência e extrai os itens exigidos usando Tool Calling do Claude.
        """
        print(f"[Processamento TR] Iniciando extração com Claude de: {pdf_path.name}")
        conteudo = self._obter_conteudo_input(pdf_path, ext_result)
        
        prompt = (
            "Você é um Arquiteto de Soluções de TI e Especialista em Licitações Públicas. "
            "Sua tarefa é analisar o Termo de Referência (TR) anexado e identificar todos os itens que estão sendo licitados. "
            "Para cada item, extraia o número do item/lote, o nome descritivo do item e a sua especificação técnica detalhada. "
            "Você DEVE responder obrigatoriamente chamando a ferramenta 'extrair_dados_tr' fornecida."
        )
        
        conteudo.append({"type": "text", "text": prompt})

        # Definição do schema do Tool
        schema_tr = {
            "type": "object",
            "properties": {
                "itens": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_num": {"type": "string", "description": "Número do item ou lote (ex: '1', 'Item 1')"},
                            "nome": {"type": "string", "description": "Nome resumido do produto ou serviço solicitado"},
                            "especificacao": {"type": "string", "description": "Especificação técnica detalhada ou exigências mínimas do item"}
                        },
                        "required": ["item_num", "nome", "especificacao"]
                    }
                }
            },
            "required": ["itens"]
        }

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            tools=[
                {
                    "name": "extrair_dados_tr",
                    "description": "Retorna os dados estruturados extraídos do Termo de Referência",
                    "input_schema": schema_tr
                }
            ],
            tool_choice={"type": "tool", "name": "extrair_dados_tr"},
            messages=[
                {"role": "user", "content": conteudo}
            ]
        )
        
        # Procura o bloco de chamada da ferramenta (tool_use) no retorno do Claude
        tool_use = next(block for block in response.content if block.type == "tool_use")
        
        # Converte o dicionário retornado diretamente para a classe Pydantic TRDados
        return TRDados.model_validate(tool_use.input)

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def extrair_proposta(self, pdf_path: Path, ext_result: dict) -> SupplierProposal:
        """
        Analisa o PDF da Proposta Comercial e extrai os dados do fornecedor usando Tool Calling do Claude.
        """
        print(f"[Processamento Proposta] Iniciando extração com Claude de: {pdf_path.name}")
        conteudo = self._obter_conteudo_input(pdf_path, ext_result)
        
        prompt = (
            "Você é um analista de licitações experiente. "
            "Analise a proposta comercial fornecida e extraia a Razão Social completa da empresa, "
            "o CNPJ do fornecedor e todos os itens ofertados, mapeando seus preços e descrições. "
            "Você DEVE responder obrigatoriamente chamando a ferramenta 'extrair_dados_proposta'."
        )
        
        conteudo.append({"type": "text", "text": prompt})

        schema_proposal = {
            "type": "object",
            "properties": {
                "razao_social": {"type": "string", "description": "Razão Social completa da empresa fornecedora"},
                "cnpj": {"type": "string", "description": "CNPJ da empresa fornecedora (formato XX.XXX.XXX/XXXX-XX ou apenas dígitos)"},
                "itens": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_num_correspondente": {"type": "string", "description": "Número do item correspondente do TR que este item atende"},
                            "descricao": {"type": "string", "description": "Descrição detalhada do item ofertado pelo fornecedor"},
                            "marca": {"type": "string", "description": "Marca do produto ofertado (se informada)"},
                            "modelo": {"type": "string", "description": "Modelo do produto ofertado (se informado)"},
                            "valor_unitario": {"type": "number", "description": "Valor unitário ofertado"},
                            "valor_total": {"type": "number", "description": "Valor total do item ofertado"}
                        },
                        "required": ["descricao"]
                    }
                }
            },
            "required": ["razao_social", "cnpj", "itens"]
        }

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            tools=[
                {
                    "name": "extrair_dados_proposta",
                    "description": "Retorna os dados estruturados da proposta do fornecedor",
                    "input_schema": schema_proposal
                }
            ],
            tool_choice={"type": "tool", "name": "extrair_dados_proposta"},
            messages=[
                {"role": "user", "content": conteudo}
            ]
        )
        
        tool_use = next(block for block in response.content if block.type == "tool_use")
        return SupplierProposal.model_validate(tool_use.input)

    @retry_on_rate_limit(max_retries=5, initial_delay=5)
    def confrontar_proposta_com_tr(self, tr_itens: List[TRItem], proposta_itens: List[ProposalItem]) -> List[ConfrontoItem]:
        """
        Compara os itens ofertados na proposta com os itens exigidos no Termo de Referência (TR).
        """
        print("[Confronto Técnico] Analisando conformidade com o Claude...")
        
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
            "Compare os itens e indique conformidades, divergências e o parecer técnico sugerido ('Aceito', 'Não aceito' ou 'Pendência'). "
            "Você DEVE responder obrigatoriamente chamando a ferramenta 'retornar_confronto'."
        )
        
        schema_confronto = {
            "type": "object",
            "properties": {
                "confrontos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_num": {"type": "string", "description": "Número do item correspondente no TR"},
                            "confronto_ia": {"type": "string", "description": "Análise técnica comparando a especificação vs proposta, destacando conformidades ou desvios específicos"},
                            "status_sugerido": {"type": "string", "description": "Status sugerido: 'Aceito', 'Não aceito', 'Pendência'"}
                        },
                        "required": ["item_num", "confronto_ia", "status_sugerido"]
                    }
                }
            },
            "required": ["confrontos"]
        }

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            tools=[
                {
                    "name": "retornar_confronto",
                    "description": "Retorna o confronto de conformidade entre os itens da proposta e do TR",
                    "input_schema": schema_confronto
                }
            ],
            tool_choice={"type": "tool", "name": "retornar_confronto"},
            messages=[
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
        )
        
        tool_use = next(block for block in response.content if block.type == "tool_use")
        parsed_res = ConfrontoResponse.model_validate(tool_use.input)
        return parsed_res.confrontos
