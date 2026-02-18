# Agente Financeiro Inteligente 💰

Este projeto é um assistente financeiro que permite registrar despesas e receitas via chat, utilizando IA (Gemini) para entender o que você escreve e salvando tudo em um banco de dados SQL.

## 🚀 Como Rodar

### 1. Pré-requisitos
Certifique-se de que o **Docker Desktop** está rodando.

### 2. Configuração
1.  Renomeie o arquivo `.env.example` para `.env`.
2.  Abra o `.env` e coloque sua **GEMINI_API_KEY**.

### 3. Iniciar o Banco de Dados
Se ainda não iniciou, rode no terminal:
```bash
docker compose up -d
```
Isso vai subir o PostgreSQL.

### 4. Inicializar a Tabela
Apenas na primeira vez, rode:
```bash
python database.py
```
Isso cria as tabelas iniciais no banco.

### 5. Rodar o App
```bash
streamlit run app.py
```
O navegador vai abrir automaticamente com o Chat e o Dashboard!

## 🛠 Tecnologias
-   **Python 3.10+**
-   **Streamlit**: Interface (Chat + Dashboard)
-   **Google Gemini**: Processamento de Linguagem Natural
-   **PostgreSQL**: Banco de Dados (via Docker)
