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

## 🚀 2. Instalação Passo a Passo

### No Windows:
1.  Localize o arquivo **`instalar_windows.bat`** na pasta do projeto.
2.  Dê um duplo-clique nele.
3.  O script vai criar o ambiente, instalar as bibliotecas e **pedir a sua API Key do Gemini**. Basta colar e dar Enter.

### Na VPS (Via Terminal/Git):
Se você quer subir o projeto direto no terminal da sua VPS Linux:

1.  **Acesse sua VPS** via SSH.
2.  **Instale o Git (se não tiver):**
    ```bash
    sudo apt update && sudo apt install git -y
    ```
3.  **Clone o Projeto:**
    ```bash
    git clone https://github.com/correaautomacoes/Agent-Financeiro.git
    cd Agent-Financeiro
    ```
4.  **Dê permissão aos scripts:**
    ```bash
    chmod +x *.sh
    ```
5.  **Execute o Instalador:**
    ```bash
    ./instalar_vps.sh
    ```
    *O script vai pedir sua GEMINI_API_KEY e subir o Banco + App automaticamente.*

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

## 🔄 3. Como atualizar o sistema na VPS?

Sempre que você fizer uma alteração no código no seu PC e quiser enviar para a VPS, siga estes passos:

1.  **No seu PC**: Faça o `Commit` e o `Push` para o GitHub.
2.  **Na VPS**: Acesse o terminal e rode:
    ```bash
    cd Agent-Financeiro
    git pull
    chmod +x atualizar_vps.sh
    ./atualizar_vps.sh
    ```
    *Dica: O `git pull` baixa os arquivos novos e o `./atualizar_vps.sh` reconstrói o sistema no Docker para aplicar as mudanças.*

---

## 🏗 5. Deploy Pro com Portainer + GitHub + Traefik (Swarm)

Se você usa Docker Swarm com Traefik, existem dois pontos críticos que causaram o erro:

1.  **Rede Externa**: O Traefik precisa que a rede `traefik_public` já exista no Swarm. 
    - Rode este comando no terminal da sua VPS antes de dar o deploy:
      ```bash
      docker network create --driver overlay traefik_public
      ```
2.  **Build no Swarm**: O comando `docker stack deploy` (usado pelo Portainer Swarm) não aceita o comando `build`. 
    - Por isso, ajustei o `docker-stack.yaml` para usar uma imagem base do Python e baixar os requisitos na hora.

### Passo a Passo no Portainer:
1.  **Suba seu projeto**: Dê Push nas novas correções do `docker-stack.yaml` para o GitHub.
2.  **No Portainer**:
    - Vá em **Stacks** > **Add Stack**.
    - Em **Build Method**, selecione **Repository**.
    - **Repository URL**: A URL do seu GitHub.
    - **Repository reference**: `refs/heads/main`
    - **Compose path**: `docker-stack.yaml`
4.  **Variáveis de Ambiente**:
    - Use a área **"Environment variables"** do Portainer para adicionar a sua `GEMINI_API_KEY`, `DB_USER`, `DB_PASSWORD`, etc. (Não use o arquivo `.env` no Git por segurança).
5.  **Deploy**: Clique em **Deploy the stack**. O Portainer vai clonar o projeto, construir a imagem e o Traefik cuidará do SSL automaticamente.

---
*Desenvolvido com ❤️ pelo Agente Financeiro.*
