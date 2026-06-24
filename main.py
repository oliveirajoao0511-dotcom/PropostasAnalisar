import argparse
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

# Importações dos módulos locais
from config import BASE_DIR, DOCS_DIR, OUTPUT_DIR, DEFAULT_UASG, DEFAULT_NUM_COMPRA, DEFAULT_OBJETO, GEMINI_API_KEY
from pdf_extractor import extract_text_from_pdf
from ai_analyzer import AIAnalyzer
from excel_generator import generate_excel_report

def setup_args():
    parser = argparse.ArgumentParser(description="Automação Analisador de Propostas Comercial")
    parser.add_argument("--uasg", type=str, default=DEFAULT_UASG, help="Código UASG do órgão licitante")
    parser.add_argument("--num-compra", type=str, default=DEFAULT_NUM_COMPRA, help="Número da Compra/Pregão")
    parser.add_argument("--objeto", type=str, default=DEFAULT_OBJETO, help="Objeto resumido da contratação")
    parser.add_argument("--tr-file", type=str, default=None, help="Caminho específico para o PDF do Termo de Referência")
    parser.add_argument("--mock", action="store_true", help="Executa uma simulação com dados fictícios (sem necessidade de API key ou PDFs reais)")
    return parser.parse_args()

def run_mock(args):
    print("=====================================================================")
    print("             MODO SIMULAÇÃO (MOCK) - ANALISADOR DE PROPOSTAS        ")
    print("=====================================================================")
    print(f"UASG: {args.uasg}")
    print(f"Número da Compra: {args.num_compra}")
    print(f"Objeto: {args.objeto}")
    print("=====================================================================")
    
    # Cria pasta de saída e documentos fictícios
    output_propostas_dir = OUTPUT_DIR / "documentos"
    output_propostas_dir.mkdir(exist_ok=True)
    
    # Cria arquivos PDF fictícios (cabeçalho PDF válido mínimo para simular abertura rápida)
    for filename in ["proposta_megatech.pdf", "proposta_inova.pdf"]:
        filepath = output_propostas_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("%PDF-1.4\n% Arquivo fictício para simulação da proposta " + filename + "\n")
            
    print("[Mock] Arquivos de proposta fictícios criados em 'saida/documentos/'.")
    
    propostas_analisadas = [
        {
            "razao_social": "MegaTech Distribuidora Ltda",
            "cnpj": "11.222.333/0001-44",
            "relative_pdf_path": "documentos/proposta_megatech.pdf",
            "itens_analisados": [
                {
                    "item_tr_num": "1",
                    "item_tr_nome": "Notebook Corporativo",
                    "descricao": "Notebook Dell Latitude 3440, Intel Core i7 12th gen, 16GB RAM, 512GB SSD, Windows 11 Pro",
                    "marca": "Dell",
                    "modelo": "Latitude 3440",
                    "valor_unitario": 4500.0,
                    "confronto_ia": "Atende integralmente às especificações do TR. O processador (i7), memória (16GB), armazenamento (512GB SSD) e sistema operacional (Windows 11 Pro) estão em perfeita conformidade.",
                    "status_sugerido": "Aceito"
                },
                {
                    "item_tr_num": "2",
                    "item_tr_nome": "Monitor 24 polegadas",
                    "descricao": "Monitor Dell P2422H 24 polegadas Full HD IPS, conexões HDMI e DisplayPort, ergonomia com regulagem de altura e inclinação",
                    "marca": "Dell",
                    "modelo": "P2422H",
                    "valor_unitario": 1200.0,
                    "confronto_ia": "Atende integralmente. Apresenta o tamanho exigido (24\"), conexões HDMI e DP, e base ergonômica com regulagem de altura e rotação.",
                    "status_sugerido": "Aceito"
                }
            ]
        },
        {
            "razao_social": "Inova Sistemas e Equipamentos Eireli",
            "cnpj": "22.333.444/0001-55",
            "relative_pdf_path": "documentos/proposta_inova.pdf",
            "itens_analisados": [
                {
                    "item_tr_num": "1",
                    "item_tr_nome": "Notebook Corporativo",
                    "descricao": "Notebook Lenovo ThinkPad E14, Intel Core i5 12th gen, 8GB RAM, 256GB SSD, Windows 11 Pro",
                    "marca": "Lenovo",
                    "modelo": "ThinkPad E14",
                    "valor_unitario": 3800.0,
                    "confronto_ia": "DIVERGÊNCIA DETECTADA: O processador ofertado é Core i5 (mínimo exigido i7), a memória RAM é de 8GB (mínimo exigido 16GB) e o armazenamento SSD é de 256GB (mínimo exigido 512GB). Item não atende aos requisitos técnicos da licitação.",
                    "status_sugerido": "Não aceito"
                },
                {
                    "item_tr_num": "2",
                    "item_tr_nome": "Monitor 24 polegadas",
                    "descricao": "Monitor LG 24MK430H 24 polegadas Full HD, conexão HDMI, base com ajuste simples de inclinação",
                    "marca": "LG",
                    "modelo": "24MK430H",
                    "valor_unitario": 850.0,
                    "confronto_ia": "PENDÊNCIA DETECTADA: O monitor ofertado não possui base ergonômica com regulagem de altura (apenas ajuste simples de inclinação). Não há menção no descritivo sobre a presença de conexão DisplayPort (apenas HDMI). Recomenda-se solicitar esclarecimentos ou desclassificar o item.",
                    "status_sugerido": "Pendência"
                }
            ]
        }
    ]
    
    output_xlsx_path = OUTPUT_DIR / "analise_propostas.xlsx"
    generate_excel_report(
        uasg=args.uasg,
        num_compra=args.num_compra,
        objeto=args.objeto,
        propostas_analisadas=propostas_analisadas,
        output_path=output_xlsx_path
    )
    print("\n=====================================================================")
    print("[Mock] Planilha de simulação gerada com sucesso!")
    print(f"Relatório Excel: {output_xlsx_path.resolve()}")
    print("Você pode testar abrindo o Excel e experimentando os dropdowns e links.")
    print("=====================================================================")

def main():
    args = setup_args()
    
    if args.mock:
        run_mock(args)
        return

    # Verifica a existência da chave de API
    if not GEMINI_API_KEY:
        print("[ERRO] GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
        print("Por favor, crie um arquivo '.env' na raiz do projeto com:")
        print("GEMINI_API_KEY=sua_chave_aqui")
        sys.exit(1)
    
    print("=====================================================================")
    print("             ANALISADOR DE PROPOSTAS COMERCIAL - INICIANDO          ")
    print("=====================================================================")
    print(f"UASG: {args.uasg}")
    print(f"Número da Compra: {args.num_compra}")
    print(f"Objeto: {args.objeto}")
    print("=====================================================================")

    # 1. Identificar arquivos
    all_pdfs = list(DOCS_DIR.glob("*.pdf"))
    if not all_pdfs:
        print(f"[Aviso] Nenhum arquivo PDF encontrado na pasta '{DOCS_DIR.resolve()}'.")
        print("Insira o Termo de Referência (com 'tr' no nome) e as propostas dos fornecedores nessa pasta.")
        sys.exit(0)

    # Identificar o Termo de Referência (TR)
    tr_path = None
    if args.tr_file:
        tr_path = Path(args.tr_file)
    else:
        # Busca automática: arquivo que contenha "tr" ou "termo" no nome
        for pdf in all_pdfs:
            name_lower = pdf.name.lower()
            if "tr" in name_lower or "termo" in name_lower or "referencia" in name_lower:
                tr_path = pdf
                break
        
        # Se não encontrar nada por nome, assume o primeiro se houver mais de um, ou pede explicitamente
        if not tr_path:
            print("[ERRO] Não foi possível identificar o PDF do Termo de Referência de forma automática.")
            print("Certifique-se de que o arquivo contenha a sigla 'TR' no nome, ou passe --tr-file <caminho>.")
            sys.exit(1)

    print(f"[Config] Termo de Referência identificado: {tr_path.name}")
    
    # As propostas são todos os PDFs na pasta, exceto o TR
    propostas_paths = [pdf for pdf in all_pdfs if pdf != tr_path]
    if not propostas_paths:
        print("[Aviso] Nenhuma proposta de fornecedor identificada além do Termo de Referência.")
        print("Insira os arquivos das propostas na pasta de documentos para análise.")
        sys.exit(0)

    print(f"[Config] Encontrada(s) {len(propostas_paths)} proposta(s) para análise.")
    print("=====================================================================")

    # Inicializa o Analisador de IA
    analyzer = AIAnalyzer()

    # 2. Extrair dados do Termo de Referência (TR)
    tr_extraction = extract_text_from_pdf(tr_path)
    try:
        tr_dados = analyzer.extrair_termos_de_referencia(tr_path, tr_extraction)
        print(f"[Sucesso] Extraídos {len(tr_dados.itens)} itens requeridos do Termo de Referência.")
        for item in tr_dados.itens:
            print(f"  - Item {item.item_num}: {item.nome}")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao processar o Termo de Referência via IA: {e}")
        sys.exit(1)

    print("=====================================================================")

    # Prepara a pasta de saída para armazenar os PDFs das propostas copiados de forma relativa
    output_propostas_dir = OUTPUT_DIR / "documentos"
    output_propostas_dir.mkdir(exist_ok=True)

    propostas_analisadas = []

    # 3. Processar cada proposta
    for prop_path in propostas_paths:
        print(f"\n[Processando] {prop_path.name}...")
        
        # Copia o arquivo original da proposta para a pasta de saída para garantir a consistência do link
        copied_dest = output_propostas_dir / prop_path.name
        shutil.copy2(prop_path, copied_dest)
        # Caminho relativo para a planilha (a planilha ficará na raiz da pasta OUTPUT_DIR)
        relative_path_for_link = f"documentos/{prop_path.name}"

        # Extrai o texto da proposta
        prop_extraction = extract_text_from_pdf(prop_path)
        
        try:
            # Extrai os dados da proposta (Fornecedor, CNPJ, itens ofertados)
            prop_dados = analyzer.extrair_proposta(prop_path, prop_extraction)
            print(f"  Fornecedor: {prop_dados.razao_social} | CNPJ: {prop_dados.cnpj}")
            print(f"  Itens Ofertados: {len(prop_dados.itens)}")
            
            # Executa a comparação/confronto dos itens da proposta com os itens do TR
            confronto_resultado = analyzer.confrontar_proposta_com_tr(
                tr_itens=tr_dados.itens,
                proposta_itens=prop_dados.itens
            )
            
            # Mapeia as informações para a estrutura da planilha
            itens_analisados = []
            for conf in confronto_resultado:
                # Busca o item original correspondente do TR para trazer o nome correto para a planilha
                tr_item_correspondente = next(
                    (x for x in tr_dados.itens if str(x.item_num) == str(conf.item_num)),
                    None
                )
                
                # Busca a descrição ofertada correspondente na proposta
                prop_item_correspondente = next(
                    (x for x in prop_dados.itens if str(x.item_num_correspondente) == str(conf.item_num)),
                    None
                )
                
                tr_nome = tr_item_correspondente.nome if tr_item_correspondente else "Item não encontrado no TR"
                desc_ofertada = prop_item_correspondente.descricao if prop_item_correspondente else "Descrição não detalhada"
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
            
            print(f"  [Sucesso] Proposta de '{prop_dados.razao_social}' analisada e confrontada.")
            
        except Exception as e:
            print(f"  [ERRO] Falha ao processar a proposta {prop_path.name}: {e}")
            continue

    # 4. Gerar Relatório Planilha
    if propostas_analisadas:
        output_xlsx_path = OUTPUT_DIR / "analise_propostas.xlsx"
        print("\n=====================================================================")
        print("             GERANDO PLANILHA DE CONSOLIDAÇÃO EXCEL                 ")
        print("=====================================================================")
        generate_excel_report(
            uasg=args.uasg,
            num_compra=args.num_compra,
            objeto=args.objeto,
            propostas_analisadas=propostas_analisadas,
            output_path=output_xlsx_path
        )
        print(f"\n[Concluído] Processo finalizado com sucesso!")
        print(f"Relatório Excel: {output_xlsx_path.resolve()}")
        print(f"Documentos PDF indexados: {output_propostas_dir.resolve()}")
    else:
        print("\n[Erro] Nenhuma proposta pôde ser analisada com sucesso. Planilha não gerada.")

if __name__ == "__main__":
    main()
