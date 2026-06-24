# Analisador de Propostas Comercial (Web App)

Este aplicativo web automatiza a extração e o confronto técnico de propostas comerciais de fornecedores com as exigências descritas no Termo de Referência (TR). 

Utiliza a API do **Google Gemini** para extração estruturada de dados e cruzamento semântico, gerando um relatório em formato Excel (.xlsx) altamente customizado, com menus dropdown interativos e hiperlinks locais para consulta imediata dos PDFs originais.

---

## 🛠️ Como Executar Localmente

### Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado no seu computador.

### Passo 1: Clone ou Copie a Pasta do Projeto
Abra o terminal no diretório do projeto.

### Passo 2: Instale as Dependências
Execute o comando abaixo para instalar todas as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### Passo 3: Configure as Variáveis de Ambiente
1. Copie o arquivo `.env.example` e renomeie para `.env`.
2. Insira sua chave de API do Gemini no arquivo `.env`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   ```

### Passo 4: Execute o Aplicativo
Inicie a interface web do Streamlit:
```bash
streamlit run app.py
```
O aplicativo abrirá automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

---

## 🌐 Como Publicar no GitHub e Hospedar na Nuvem (Gratuito)

Você pode publicar este projeto no **GitHub** e colocá-lo no ar no **Streamlit Community Cloud** para que qualquer pessoa do seu setor acesse através de um link de forma segura.

### Passo A: Criar Repositório no GitHub
1. Crie uma conta no [GitHub](https://github.com/) (se não tiver).
2. Crie um novo repositório chamado `analisador-de-propostas`.
3. Adicione os arquivos do projeto a este repositório.
   *   **⚠️ IMPORTANTE:** Nunca publique o arquivo `.env` contendo a sua API Key real no GitHub. O arquivo `.gitignore` padrão do git impede isso. Deixe apenas o `.env.example`.

### Passo B: Criar Conta no Streamlit Cloud
1. Acesse [Streamlit Community Cloud](https://share.streamlit.io/) e faça login usando a sua conta do GitHub.
2. Clique em **"New app"** (Novo aplicativo).

### Passo C: Configurar o Deploy
Preencha os campos da seguinte forma:
- **Repository:** Selecione o seu repositório `seu-usuario/analisador-de-propostas`
- **Branch:** `main` (ou `master`)
- **Main file path:** `app.py`

### Passo D: Configurar a Chave do Gemini com Segurança
Antes de clicar em Deploy:
1. Clique em **"Advanced Settings"** (Configurações Avançadas) no formulário do Streamlit.
2. Na área **"Secrets"**, digite a sua chave de API conforme abaixo:
   ```toml
   GEMINI_API_KEY = "sua-api-key-real-aqui"
   ```
3. Salve e clique em **"Deploy!"**.

O aplicativo será construído em alguns minutos e você receberá um link público (ex: `https://analisador-de-propostas.streamlit.app`) para compartilhar com a sua seção! Os usuários poderão usar suas próprias chaves de API digitando diretamente na barra lateral se preferirem não deixar uma fixa.
