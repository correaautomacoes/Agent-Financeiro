# Agente Financeiro Inteligente 💰

Este projeto é um assistente financeiro que permite registrar despesas e receitas via chat, utilizando IA (Gemini) para entender o que você escreve e salvando tudo em um banco de dados SQL.

## 🚀 Como Rodar Localmente (Windows)

O sistema foi preparado para ser instalado com apenas alguns cliques.

### 1. Pré-requisitos
- **Windows 10 ou 11**.
- **Python 3.10+** (Certifique-se de marcar "Add Python to PATH").
- **Docker Desktop** instalado e rodando (Para o Banco de Dados).

### 2. Instalação e Configuração
1.  Execute o arquivo **`instalar_windows.bat`** com um duplo clique.
2.  O instalador irá:
    - Criar o ambiente isolado (venv).
    - Instalar todas as dependências.
    - Solicitar sua **GEMINI_API_KEY** (Cole sua chave e dê Enter).
    - Iniciar o banco de dados via Docker.
    - Criar um **atalho na área de trabalho** chamado "Agente Financeiro".

### 3. Acesso
- Após a instalação, basta usar o atalho na sua Área de Trabalho ou rodar o arquivo **`run_app.bat`**.
- O sistema abrirá automaticamente no seu navegador.

## 🛠 Tecnologias
-   **Python 3.10+**
-   **Streamlit**: Interface (Chat + Dashboard)
-   **Google Gemini**: Processamento de Linguagem Natural
-   **PostgreSQL**: Banco de Dados (via Docker)
