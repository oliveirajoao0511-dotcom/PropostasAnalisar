# Analisador de Propostas Comercial (Web App - Anthropic Claude)

Este aplicativo web automatiza a extração e o confronto técnico de propostas comerciais de fornecedores com as exigências descritas no Termo de Referência (TR). 

Utiliza a API do **Anthropic Claude 3.5 Sonnet** (via Tool Calling e processamento nativo de PDFs) para extração estruturada de dados e cruzamento semântico, gerando um relatório em formato Excel (.xlsx) altamente customizado, com menus dropdown interativos e hiperlinks locais para consulta imediata dos PDFs originais.

---

## 🛠️ Como Executar Localmente

### Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado no seu computador.

### Passo 1: Instale as Dependências
Execute o comando abaixo para instalar todas as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### Passo 2: Configure as Variáveis de Ambiente
1. Copie o arquivo `.env.example` e renomeie para `.env`.
2. Insira sua chave de API da Anthropic no arquivo `.env`:
   ```env
   ANTHROPIC_API_KEY=sua_chave_aqui
   ```

### Passo 3: Execute o Aplicativo
Inicie a interface web do Streamlit:
```bash
streamlit run app.py
```
O aplicativo abrirá automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

---

## 🌐 Como Publicar no GitHub e Hospedar no Render

Você pode hospedar este projeto de forma pública ou privada no **Render** com deploy automático a partir do seu repositório no **GitHub**.

### Passo A: Enviar para o GitHub
Envie todos os arquivos do projeto para o seu repositório.
*   **⚠️ IMPORTANTE:** Nunca publique o arquivo `.env` contendo a sua API Key real no GitHub. O arquivo `.gitignore` padrão impede isso.

### Passo B: Configurar no Render.com
1. Crie um novo **Web Service** e conecte o repositório do seu GitHub.
2. Defina os seguintes parâmetros no painel do Render:
   - **Language:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - **Plan:** `Free`

### Passo C: Configurar a Chave da Anthropic no Render
1. Vá para a aba **"Environment"** do seu Web Service no Render.
2. Adicione a seguinte variável chave-valor:
   *   **Key:** `ANTHROPIC_API_KEY`
   *   **Value:** *(Cole a sua chave de API obtida no Anthropic Console)*
3. Clique em **"Save Changes"**. O Render fará o deploy e gerará o link acessível para a sua equipe!
