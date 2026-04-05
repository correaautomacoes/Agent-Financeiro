# 🚀 INSTALAÇÃO RÁPIDA - Agente Financeiro

## Windows

### Opção 1: Automática (Recomendado)
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

### Opção 2: Manual
```bash
python setup.py
```

---

## Linux / macOS

```bash
bash setup.sh
```

ou

```bash
python3 setup.py
```

---

## Após Instalação

### Adicionar sua chave de API (Google Gemini)

1. Obtenha uma chave gratuita em: https://aistudio.google.com/app/apikeys
2. Edite o arquivo `.env` e atualize:
   ```
   GEMINI_API_KEY=sua-chave-aqui
   ```

### Iniciar a Aplicação

#### Windows
- Duplo clique em `run.bat`
- Ou: `python -m streamlit run app.py`

#### Linux/macOS
- `./run.sh`
- Ou: `python3 -m streamlit run app.py`

A aplicação abrirá em: **http://localhost:8502**

---

## 📦 Restaurar Dados de Backup

Ao executar o `setup.py`, o instalador **detecta automaticamente** seus backups anteriores e oferece restaurá-los!

Se tiver backups em arquivo separado:
- Coloque seu arquivo `*.db` ou `*.sql` no diretório do projeto
- Execute `setup.py` novamente e selecione qual restaurar

---

## 🔄 Migração entre Computadores

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/Agent-Financeiro.git
   cd Agent-Financeiro
   ```

2. **Execute o setup:**
   - Windows: `powershell -ExecutionPolicy Bypass -File setup.ps1`
   - Linux/macOS: `bash setup.sh`

3. **O instalador automaticamente:**
   - ✓ Cria ambiente isolado (venv)
   - ✓ Instala todas as dependências
   - ✓ Detecta arquivos de backup
   - ✓ Oferece restaurar dados anteriores
   - ✓ Cria scripts de inicialização

---

## 🐛 Troubleshooting

### "Python não encontrado"
- Instale Python 3.10+ de: https://www.python.org
- Marque a opção **"Add Python to PATH"** durante instalação

### Erro de privilégios no PowerShell (Windows)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
powershell -ExecutionPolicy Bypass -File setup.ps1
```

### Conexão com banco de dados
- Por padrão usa **SQLite local** (sem dependências)
- Se quiser PostgreSQL + Docker, o setup questiona durante instalação

### Port 8502 já em uso
```bash
python -m streamlit run app.py --server.port 8503
```

---

## 📚 Mais Informações

Consulte `README.md` para documentação completa do projeto.
