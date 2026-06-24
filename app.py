import os
import shutil
import tempfile
from pathlib import Path
import streamlit as st

# Carrega os módulos locais da automação
from pdf_extractor import extract_text_from_pdf
from ai_analyzer import AIAnalyzer
from excel_generator import generate_excel_report

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Analisador de Propostas Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada para um visual moderno e limpo (Classic Navy)
st.markdown("""
<style>
    .main-title {
        color: #1F4E78;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .subtitle {
        color: #595959;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 16px;
        margin-bottom: 25px;
    }
    .section-header {
        color: #2F5597;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 600;
        border-bottom: 2px solid #D9E1F2;
        padding-bottom: 8px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Cabeçalho Principal
st.markdown("<h1 class='main-title'>📊 Analisador de Propostas Comercial</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Extração de dados via OCR/IA e Confronto Técnico automatizado de propostas de fornecedores com o Termo de Referência (TR).</p>", unsafe_allow_html=True)

# =====================================================================
# CONFIGURAÇÃO DA SIDEBAR (Chave de API)
# =====================================================================
st.sidebar.markdown("### ⚙️ Configurações de API")

# Tenta carregar a chave de API das variáveis de ambiente ou segredos do Streamlit
default_api_key = os.getenv("GEMINI_API_KEY", "")
if not default_api_key and "GEMINI_API_KEY" in st.secrets:
    default_api_key = st.secrets["GEMINI_API_KEY"]

api_key_input = st.sidebar.text_input(
    "Chave de API do Gemini",
    value=default_api_key,
    type="password",
    help="Obtenha uma chave gratuita no Google AI Studio (https://aistudio.google.com/)"
)

# Injeta a chave de API na configuração para o ai_analyzer ler
if api_key_input:
    os.environ["GEMINI_API_KEY"] = api_key_input

# Seleção de Modelo para contornar instabilidades/altas demandas temporárias
model_selection = st.sidebar.selectbox(
    "Modelo de IA (Gemini)",
    options=["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"],
    index=0,
    help="Caso o modelo selecionado apresente erro 503 (indisponível/alta demanda), selecione outra versão (ex: gemini-1.5-flash) e tente novamente."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📖 Como usar:
1. Insira os dados gerais do Pregão.
2. Faça o upload do **Termo de Referência** (PDF contendo as exigências).
3. Faça o upload das **Propostas dos Fornecedores** (um ou mais PDFs).
4. Clique em **'Iniciar Análise Técnica'**.
5. Ao concluir, baixe o **Arquivo ZIP** contendo a planilha Excel (.xlsx) e os PDFs originais correspondentes.
""")

# =====================================================================
# FORMULÁRIO PRINCIPAL DE DADOS
# =====================================================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("<h3 class='section-header'>📝 Dados Gerais da Contratação</h3>", unsafe_allow_html=True)
    uasg = st.text_input("Código UASG", value="120001", help="Código do órgão licitante")
    num_compra = st.text_input("Número da Compra / Pregão", value="05/2026", help="Identificação da licitação")
    objeto = st.text_area(
        "Objeto da Licitação", 
        value="Aquisição de computadores portáteis e periféricos para a Administração Pública",
        height=100
    )

with col2:
    st.markdown("<h3 class='section-header'>📂 Upload de Documentos (PDF)</h3>", unsafe_allow_html=True)
    
    # Upload do Termo de Referência
    tr_file = st.file_uploader(
        "PDF do Termo de Referência (TR)",
        type=["pdf"],
        help="Carregue o arquivo contendo a especificação técnica dos itens."
    )
    
    # Upload das Propostas
    propostas_files = st.file_uploader(
        "PDF(s) das Propostas Técnicas/Comerciais",
        type=["pdf"],
        accept_multiple_files=True,
        help="Carregue uma ou mais propostas dos fornecedores."
    )

st.markdown("---")

# Botão de Ação
btn_analise = st.button("🚀 Iniciar Análise Técnica", use_container_width=True)

if btn_analise:
    # Validações Iniciais
    if not api_key_input:
        st.error("❌ Por favor, informe a Chave de API do Gemini na barra lateral para continuar.")
    elif not tr_file:
        st.error("❌ Por favor, carregue o PDF do Termo de Referência (TR).")
    elif not propostas_files:
        st.error("❌ Por favor, carregue ao menos uma Proposta de fornecedor.")
    else:
        # Cria um diretório temporário isolado para a execução
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # Subpastas temporárias
            docs_dir = temp_dir / "documentos"
            saida_dir = temp_dir / "saida"
            saida_docs_dir = saida_dir / "documentos"
            
            docs_dir.mkdir(parents=True, exist_ok=True)
            saida_docs_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. Salvar os arquivos carregados no diretório temporário
            tr_path = docs_dir / tr_file.name
            with open(tr_path, "wb") as f:
                f.write(tr_file.getbuffer())
                
            for p_file in propostas_files:
                p_path = docs_dir / p_file.name
                with open(p_path, "wb") as f:
                    f.write(p_file.getbuffer())
            
            # Interface de Progresso
            prog_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Inicializa o analisador de IA com o modelo selecionado
                status_text.markdown(f"🔄 *Inicializando motor de Inteligência Artificial ({model_selection})...*")
                analyzer = AIAnalyzer(model_name=model_selection)
                prog_bar.progress(10)
                
                # 2. Extrair dados do Termo de Referência (TR)
                status_text.markdown(f"📖 *Lendo especificações do Termo de Referência: **{tr_file.name}**...*")
                tr_extraction = extract_text_from_pdf(tr_path)
                tr_dados = analyzer.extrair_termos_de_referencia(tr_path, tr_extraction)
                prog_bar.progress(30)
                
                # Exibe resumo dos itens do TR identificados
                with st.expander("✅ Itens identificados no Termo de Referência", expanded=False):
                    for item in tr_dados.itens:
                        st.markdown(f"**Item {item.item_num}: {item.nome}**")
                        st.caption(item.especificacao)
                
                propostas_analisadas = []
                num_propostas = len(propostas_files)
                
                # 3. Processar cada Proposta
                for idx, p_file in enumerate(propostas_files):
                    status_text.markdown(f"⚡ *Analisando proposta **{p_file.name}** ({idx + 1} de {num_propostas})...*")
                    p_path = docs_dir / p_file.name
                    
                    # Copia a proposta original para a pasta de saída para o hiperlink relativo
                    shutil.copy2(p_path, saida_docs_dir / p_file.name)
                    relative_path_for_link = f"documentos/{p_file.name}"
                    
                    # Processamento local de texto e OCR
                    prop_extraction = extract_text_from_pdf(p_path)
                    
                    # Extração com IA
                    prop_dados = analyzer.extrair_proposta(p_path, prop_extraction)
                    
                    # Confronto técnico
                    confronto_resultado = analyzer.confrontar_proposta_com_tr(
                        tr_itens=tr_dados.itens,
                        proposta_itens=prop_dados.itens
                    )
                    
                    # Estruturação para a planilha
                    itens_analisados = []
                    for conf in confronto_resultado:
                        tr_item_correspondente = next(
                            (x for x in tr_dados.itens if str(x.item_num) == str(conf.item_num)),
                            None
                        )
                        prop_item_correspondente = next(
                            (x for x in prop_dados.itens if str(x.item_num_correspondente) == str(conf.item_num)),
                            None
                        )
                        
                        tr_nome = tr_item_correspondente.nome if tr_item_correspondente else "Não encontrado no TR"
                        desc_ofertada = prop_item_correspondente.descricao if prop_item_correspondente else "Descrição omissa"
                        marca = prop_item_correspondente.marca if prop_item_correspondente else "N/A"
                        modelo = prop_item_correspondente.modelo if prop_item_correspondente else "N/A"
                        val_uni = prop_item_correspondente.valor_unitario if prop_item_correspondente else 0.0
                        
                        itens_analisados.append({
                            "item_tr_num": conf.item_num,
                            "item_tr_nome": tr_nome,
                            "descricao": desc_ofertada,
                            "marca": marca,
                            "modelo": modelo,
                            "valor_unitario": val_uni,
                            "confronto_ia": conf.confronto_ia,
                            "status_sugerido": conf.status_sugerido
                        })
                        
                    propostas_analisadas.append({
                        "razao_social": prop_dados.razao_social,
                        "cnpj": prop_dados.cnpj,
                        "relative_pdf_path": relative_path_for_link,
                        "itens_analisados": itens_analisados
                    })
                    
                    # Incrementa progresso proporcionalmente
                    prog_val = 30 + int((idx + 1) / num_propostas * 50)
                    prog_bar.progress(prog_val)
                
                # 4. Gerar Relatório Planilha
                status_text.markdown("📋 *Estruturando e estilizando planilha Excel final...*")
                output_xlsx_path = saida_dir / "analise_propostas.xlsx"
                generate_excel_report(
                    uasg=uasg,
                    num_compra=num_compra,
                    objeto=objeto,
                    propostas_analisadas=propostas_analisadas,
                    output_path=output_xlsx_path
                )
                prog_bar.progress(90)
                
                # 5. Compactar a pasta de saída em ZIP (Planilha + Documentos)
                status_text.markdown("📦 *Criando pacote ZIP para download...*")
                zip_base_name = temp_dir / "resultado_analise"
                # make_archive gera o arquivo zip no caminho especificado
                zip_archive_path = Path(shutil.make_archive(zip_base_name, 'zip', saida_dir))
                
                # Carrega o arquivo ZIP em memória para disponibilizar no download_button
                with open(zip_archive_path, "rb") as f:
                    zip_bytes = f.read()
                
                prog_bar.progress(100)
                status_text.success("✨ **Análise concluída com sucesso!**")
                
                # Seção de Resultados e Downloads
                st.markdown("<h3 class='section-header'>🎁 Download dos Resultados</h3>", unsafe_allow_html=True)
                
                st.info(
                    "💡 **Instruções:** O download contém um arquivo `.zip`. Extraia a pasta completa. "
                    "A planilha Excel estará na raiz da pasta e os arquivos PDF originais estarão na pasta `documentos/`. "
                    "Isso garante que os links para abrir os PDFs diretamente de dentro do Excel funcionem perfeitamente."
                )
                
                st.download_button(
                    label="📥 Baixar Pasta de Análise Completa (Planilha + PDFs)",
                    data=zip_bytes,
                    file_name=f"analise_pregao_uasg_{uasg}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
            except Exception as e:
                status_text.error(f"❌ Ocorreu um erro inesperado durante o processamento: {e}")
                st.exception(e)
