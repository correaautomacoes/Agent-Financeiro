# Guia de Instalação - Agente Financeiro Inteligente 💰

Este guia explica como configurar o sistema do zero, seja para uso **Local (sua máquina)** ou para **Hospedagem em VPS**.

---

## 🛠 1. Pré-Requisitos (O que você precisa instalar antes)

Antes de rodar os instaladores, certifique-se de ter os seguintes softwares em sua máquina:

1.  **Python 3.10 ou superior**: Necessário para rodar o cérebro do sistema.
    - [Baixar Python aqui](https://www.python.org/downloads/)
    - *Importante:* No Windows, marque a opção **"Add Python to PATH"** durante a instalação.
2.  **Docker Desktop**: Necessário para rodar o banco de dados PostgreSQL de forma simples.
    - [Baixar Docker aqui](https://www.docker.com/products/docker-desktop/)
3.  **Chave de API do Gemini**: 
    - Obtenha sua chave gratuita no [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## 🚀 2. Instalação "Um-Clique" (Recomendado)

Desenvolvemos scripts que automatizam todo o processo de configuração:

### No Windows:
1.  Localize o arquivo **`instalar_windows.bat`** na pasta do projeto.
2.  Dê um duplo-clique nele.
3.  O script vai criar o ambiente, instalar as bibliotecas e **pedir a sua API Key do Gemini**. Basta colar e dar Enter.
4.  O sistema abrirá automaticamente no final!

### Na VPS (Linux/Ubuntu):
1.  Mande a pasta do projeto para sua VPS.
2.  No terminal, dê permissão ao instalador: `chmod +x instalar_vps.sh`
3.  Rode o script: `./instalar_vps.sh`
4.  Siga as instruções na tela para configurar sua API Key.

---

## 📂 3. Como disponibilizar para outras pessoas?

Se você é o dono do projeto e quer enviar para alguém, siga este checklist para segurança:

1.  **O que APAGAR antes de enviar:**
    - ❌ Arquivo `.env`: Contém a SUA chave de API. Se enviar, outras pessoas usarão seus créditos.
    - ❌ Pasta `venv`: É uma pasta pesada e específica do seu PC. O instalador cria uma nova no PC do outro.
    - ❌ Pasta `__pycache__`: Lixo de execução do Python.
2.  **O que ENVIAR:**
    - ✅ Todas as outras pastas e arquivos (`app.py`, `database.py`, `.env.example`, etc.).
3.  **Como enviar:**
    - Transforme a pasta em um arquivo **.zip** e envie para a pessoa.

---

## 🔒 Segurança em Produção (VPS)
- **Porta padrão**: O Streamlit roda na porta `8501`. Garanta que ela esteja aberta no seu firewall.
- **HTTPS**: Para uso profissional em VPS, recomendamos configurar um Proxy Reverso com Nginx e SSL (Certbot/LetsEncrypt).
- **Banco de Dados**: As senhas padrão no `.env.example` são para facilitar a instalação. Recomendamos trocar por senhas fortes antes de colocar o sistema "na rua".

---

## 🔄 4. Como atualizar o sistema na VPS?

Se você fez ajustes no código e quer subir as alterações para a VPS:

1.  Envie os novos arquivos para a pasta do projeto na VPS (substituindo os antigos).
2.  No terminal da VPS, rode o script de atualização:
    ```bash
    chmod +x atualizar_vps.sh
    ./atualizar_vps.sh
    ```
    *Dica: Esse comando reconstrói apenas a parte do código, sem apagar os seus dados salvos no banco de dados.*

---

## 🏗 5. Deploy Pro com Portainer + GitHub + Traefik

Esta é a forma recomendada para manter o sistema sempre atualizado:

1.  **Suba seu projeto**: Coloque seu código no seu GitHub.
2.  **No Portainer**:
    - Vá em **Stacks** > **Add Stack**.
    - Em **Build Method**, selecione **Repository**.
    - Cole a URL do seu GitHub (ex: `https://github.com/seu-usuario/erp-agente`).
    - Se o repositório for privado, configure o **Personal Access Token**.
3.  **Configuração da Stack**:
    - Nome: `erp-agente`.
    - **Repository reference**: `refs/heads/main`
    - **Compose path**: `docker-stack.yaml`
4.  **Variáveis de Ambiente**:
    - Use a área **"Environment variables"** do Portainer para adicionar a sua `GEMINI_API_KEY`, `DB_USER`, `DB_PASSWORD`, etc. (Não use o arquivo `.env` no Git por segurança).
5.  **Deploy**: Clique em **Deploy the stack**. O Portainer vai clonar o projeto, construir a imagem e o Traefik cuidará do SSL automaticamente.

---
*Desenvolvido com ❤️ pelo Agente Financeiro.*
