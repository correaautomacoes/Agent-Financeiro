# Agente Financeiro Inteligente 💰

Este projeto é um assistente financeiro que permite registrar despesas e receitas via chat, utilizando IA (Gemini) para entender o que você escreve e salvando tudo em um banco de dados SQL.

## 🚀 Como Rodar Localmente (RÁPIDO)

### Setup Automático (Cross-Platform - Windows/Linux/macOS)

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

**Linux/macOS:**
```bash
bash setup.sh
```

Ou execute o Python diretamente em qualquer sistema:
```bash
python setup.py
```

### O que o Setup Faz Automaticamente
✅ Verifica/instala Python 3.10+  
✅ Cria virtual environment isolado  
✅ Instala todas as dependências  
✅ **Detecta e oferece restaurar seus backup anteriores**  
✅ Configura arquivo `.env`  
✅ Inicializa banco de dados  
✅ Cria scripts de inicialização  

### Pré-requisitos Mínimos
- **Python 3.10+** (https://www.python.org)
- **Git** (opcional, para clonar o repositório)
- **Google Gemini API Key** (gratuita em https://aistudio.google.com/app/apikeys)

### Após Instalação
1. Atualize seu `.env` com a GEMINI_API_KEY
2. Execute `run.bat` (Windows) ou `./run.sh` (Linux/macOS)
3. Acesse em: http://localhost:8502

---

## 📱 Migração entre Computadores

O processo agora é **completamente automatizado**! 

### Passo a Passo:
1. **Clone o repositório no novo computador:**
   ```bash
   git clone https://github.com/seu-usuario/Agent-Financeiro.git
   cd Agent-Financeiro
   ```

2. **Execute o setup:**
   ```powershell
   # Windows
   powershell -ExecutionPolicy Bypass -File setup.ps1
   ```
   ```bash
   # Linux/macOS
   bash setup.sh
   ```

3. **O setup automaticamente detectará seus backups** e oferecerá restaurar!

### Gerenciador de Backups
Para gerenciar backups manualmente:
```bash
python backup_manager.py --interactive
python backup_manager.py --create --desc "Backup antes de atualização"
python backup_manager.py --list
python backup_manager.py --restore "backups/20260403_xxxxxx_backup_lite_xxxxxx.db"
```

---

## 🛠 Tecnologias
-   **Python 3.10+**
-   **Streamlit**: Interface (Chat + Dashboard)
-   **Google Gemini**: Processamento de Linguagem Natural
-   **PostgreSQL**: Banco de Dados (via Docker)
