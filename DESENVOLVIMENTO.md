# 👨‍💻 Guia de Desenvolvimento

## Estrutura do Projeto

```
Agent-Financeiro/
├── app.py                    # Interface Streamlit (principal)
├── ai_agent.py              # Integração com Google Gemini
├── database.py              # Conexão e queries do BD
├── db_helpers.py            # Funções auxiliares do BD
├── backup_utils.py          # Funções de backup/restore
├── backup_manager.py        # CLI para gerenciar backups
│
├── setup.py                 # Instalador interativo (Python)
├── setup.sh                 # Instalador interativo (Linux/macOS)
├── setup.ps1                # Instalador interativo (PowerShell)
│
├── requirements.txt         # Dependências Python
├── .env.example             # Exemplo de configuração
├── docker-compose.yaml      # Config Docker (PostgreSQL)
└── README.md / INSTALACAO_RAPIDA.md
```

## Desenvolvimento Local

### 1. Setup para Development

```bash
# Clone e entre no diretório
git clone https://github.com/seu-usuario/Agent-Financeiro.git
cd Agent-Financeiro

# Execute o setup (automático)
python setup.py

# Ou crie ambient manual
python -m venv venv

# Ative venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
```

### 2. Configuração .env para Desenvolvimento

```env
# Use SQLite para desenvolvimento local
DB_TYPE=sqlite
SQLITE_PATH=financeiro_dev.db
GEMINI_API_KEY=sua-chave-aqui
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### 3. Rodar em Desenvolvimento

```bash
# Terminal 1: Streamlit em modo watch
python -m streamlit run app.py

# A aplicação recarrega automaticamente ao salvar arquivos!
```

### 4. Debug

```bash
# Ver logs do streamlit
python -m streamlit run app.py --logger.level=debug

# Testar queries do BD
python check_db.py

# Testar modelos de IA
python test_models.py
```

---

## Variáveis de Ambiente (Completas)

### Banco de Dados

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DB_TYPE` | `sqlite` | Tipo de BD: `sqlite` ou `postgres` |
| `SQLITE_PATH` | `financeiro.db` | Caminho SQLite (relativo ao projeto) |
| `DB_HOST` | `postgres` | Host PostgreSQL |
| `DB_PORT` | `5432` | Porta PostgreSQL |
| `DB_NAME` | `financial_db` | Nome do banco PostgreSQL |
| `DB_USER` | `admin` | Usuário PostgreSQL |
| `DB_PASSWORD` | `admin_password` | Senha PostgreSQL |

### APIs

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GEMINI_API_KEY` | `` | Chave Google Gemini (obtenha em https://aistudio.google.com/app/apikeys) |

### Streamlit

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | Desabilitar telemetria |
| `STREAMLIT_SERVER_PORT` | `8502` | Porta do servidor |

---

## Workflow: Desenvolvimento → Produção

### 1. Desenvolvimento (SQLite Local)
```env
DB_TYPE=sqlite
SQLITE_PATH=financeiro_dev.db
```

### 2. Testes com Docker (PostgreSQL)
```bash
# Inicie PostgreSQL
docker-compose up -d

# Configure .env
DB_TYPE=postgres
DB_HOST=localhost  # ou 127.0.0.1
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=admin_password
DB_NAME=financial_db

# Rode aplicação
python -m streamlit run app.py
```

### 3. Deploy em VPS
```bash
# SSH na VPS
ssh user@seu-server

# Clone projeto
git clone seu-repo

# Execute setup
python3 setup.py

# Ou inicie com Docker
docker-compose up -d
```

---

## Backup & Dados

### Criar Backup Automático

```bash
# Via CLI interativa
python backup_manager.py --interactive

# Via comando
python backup_manager.py --create --desc "Feature: adicionado X"
```

### Restaurar Backup

```bash
# Interativo
python backup_manager.py --interactive
# Escolha opção [3] Restaurar

# Via comando
python backup_manager.py --restore "backups/20260403_120000_backup_lite.db"
```

### Copiar Dados para Novo Computador

```bash
# No computador antigo:
python backup_manager.py --create --desc "Backup antes de migração"

# Copie o arquivo de backup para o novo computador:
# backups/20260403_xxxxxx.db → novo-computador/backups/

# No computador novo:
python setup.py
# Escolha restaurar o backup!
```

---

## Comandos Úteis

### Limpeza & Manutenção

```bash
# Limpar cache Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remover venv
rm -rf venv/

# Reset completo do BD
rm financeiro.db
python -c "from database import init_db; init_db()"
```

### Desenvolvimento

```bash
# Instalar dependência nova
pip install seu-pacote
pip freeze > requirements.txt

# Verificar dependências desatualizadas
pip list --outdated

# Verificar erros de lint
python -m flake8 app.py
```

### Docker

```bash
# Ver logs do PostgreSQL
docker logs financial_agent_db

# Conectar ao PostgreSQL
docker exec -it financial_agent_db psql -U admin -d financial_db

# Parar tudo
docker-compose down

# Remover volumes (PERDA DE DADOS!)
docker-compose down -v
```

---

## Contribute

1. Crie uma branch: `git checkout -b feature/minha-feature`
2. Faça commits: `git commit -m "Adicionar X"`
3. Faça backup antes de grandes mudanças: `python backup_manager.py --create`
4. Push e abra PR

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'streamlit'"
```bash
pip install -r requirements.txt
```

### Porta 8502 já em uso
```bash
python -m streamlit run app.py --server.port 8503
```

### Erro de permissão no PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Database locked (SQLite)
```bash
# Feche todas as conexões abertas
# Ou use: rm financeiro.db (e recrie com setup.py)
```

---

## Referências

- [Streamlit Documentation](https://docs.streamlit.io)
- [Google Gemini API](https://ai.google.dev)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
