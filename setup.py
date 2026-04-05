#!/usr/bin/env python3
"""
SETUP INTERATIVO - Agente Financeiro
Instala o projeto completamente em um novo computador e restaura dados de backup se disponível.
Cross-platform (Windows, Linux, macOS)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def check_python():
    """Verifica se Python 3.10+ está instalado"""
    print_info(f"Python version: {sys.version}")
    if sys.version_info < (3, 10):
        print_error("Python 3.10+ é obrigatório!")
        sys.exit(1)
    print_success("Python 3.10+ encontrado")

def check_pip():
    """Verifica pip"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        print_success("pip encontrado")
    except:
        print_error("pip não encontrado!")
        sys.exit(1)

def create_venv():
    """Cria virtual environment"""
    venv_path = Path("venv")
    if venv_path.exists():
        print_warning(f"Virtual environment já existe em {venv_path}")
        response = input("Deseja recriá-lo? (s/n): ").lower()
        if response == 's':
            shutil.rmtree(venv_path)
        else:
            print_success("Usando venv existente")
            return
    
    print_info("Criando virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    print_success("Virtual environment criado")

def get_pip_executable():
    """Retorna o caminho do pip correto (Windows ou Unix)"""
    if sys.platform == "win32":
        return Path("venv/Scripts/pip.exe")
    else:
        return Path("venv/bin/pip")

def install_dependencies():
    """Instala dependências do requirements.txt"""
    print_info("Instalando dependências...")
    pip_exe = get_pip_executable()
    
    subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(pip_exe), "install", "-r", "requirements.txt"], check=True)
    
    print_success("Dependências instaladas")

def setup_env():
    """Cria ou atualiza arquivo .env"""
    env_path = Path(".env")
    
    if env_path.exists():
        print_warning(".env já existe")
        response = input("Deseja reconfigurá-lo? (s/n): ").lower()
        if response != 's':
            print_info("Mantendo .env existente")
            return
    
    print_header("CONFIGURAÇÃO .env")
    
    # Tipo de banco de dados
    print("Escolha o banco de dados:")
    print("  [1] SQLite (Local, recomendado para desenvolvimento)")
    print("  [2] PostgreSQL (Com Docker)")
    db_choice = input("Opção (1 ou 2): ").strip() or "1"
    
    db_type = "sqlite" if db_choice == "1" else "postgres"
    
    # API Key do Gemini
    print_info("Você pode obter uma chave gratuita em: https://aistudio.google.com/app/apikeys")
    gemini_key = input("Cole sua GEMINI_API_KEY (ou deixe vazio por enquanto): ").strip()
    
    # Criar .env
    env_content = f"""# Configuração Agente Financeiro
# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DB_TYPE={db_type}

# SQLite (Development)
SQLITE_PATH=financeiro.db

# PostgreSQL (Production - Docker)
DB_HOST=postgres
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=admin_password
DB_NAME=financial_db

# API Keys
GEMINI_API_KEY={gemini_key if gemini_key else 'sua-chave-aqui'}
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print_success(f".env criado em {env_path}")
    if not gemini_key:
        print_warning("Você precisa adicionar GEMINI_API_KEY no .env depois")

def find_backups():
    """Encontra backups de banco de dados disponíveis"""
    project_dir = Path(".")
    backups = list(project_dir.glob("*.db")) + list(project_dir.glob("*.sql"))
    
    # Filtra os backups relevantes
    relevant_backups = [
        b for b in backups 
        if any(x in b.name for x in ["backup", "financeiro_dev", "financeiro"])
        and "thumbcache" not in b.name
    ]
    
    return sorted(relevant_backups, key=lambda x: x.stat().st_mtime, reverse=True)

def restore_backup():
    """Oferece opção de restaurar backup"""
    print_header("RESTAURAR DADOS")
    
    backups = find_backups()
    
    if not backups:
        print_warning("Nenhum backup de dados encontrado no diretório")
        return False
    
    print_info(f"Encontrados {len(backups)} backup(s):")
    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  [{i}] {backup.name} ({size_mb:.2f}MB) - {mod_time}")
    
    print("\n  [0] Não restaurar agora")
    choice = input(f"\nEscolha o backup (0-{len(backups)}): ").strip()
    
    try:
        choice_idx = int(choice)
        if choice_idx == 0:
            print_info("Continuando sem restaurar...")
            return False
        
        if 1 <= choice_idx <= len(backups):
            selected_backup = backups[choice_idx - 1]
            
            # Copiar backup para financeiro.db (padrão)
            target = Path("financeiro.db")
            shutil.copy2(selected_backup, target)
            print_success(f"Backup '{selected_backup.name}' restaurado para '{target}'")
            return True
    except (ValueError, IndexError):
        print_error("Opção inválida!")
    
    return False

def init_database():
    """Inicializa banco de dados"""
    print_info("Inicializando banco de dados...")
    try:
        from database import init_db
        init_db()
        print_success("Banco de dados inicializado")
    except Exception as e:
        print_warning(f"Erro ao inicializar BD: {e}")

def create_startup_script():
    """Cria scripts de inicialização"""
    print_info("Criando scripts de inicialização...")
    
    if sys.platform == "win32":
        # Windows
        script_content = """@echo off
cd /d "%~dp0"
python -m streamlit run app.py
pause
"""
        script_path = Path("run.bat")
    else:
        # Unix/Linux/macOS
        script_content = """#!/bin/bash
cd "$(dirname "$0")"
python -m streamlit run app.py
"""
        script_path = Path("run.sh")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    if sys.platform != "win32":
        os.chmod(script_path, 0o755)
    
    print_success(f"Script de inicialização criado: {script_path}")

def print_next_steps():
    """Exibe próximos passos"""
    print_header("INSTALAÇÃO CONCLUÍDA! 🎉")
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}")
    print("Próximos passos:")
    print(f"{Colors.ENDC}")
    print("1. Atualize o arquivo .env com sua GEMINI_API_KEY se não adicionou")
    print("   - Obtenha em: https://aistudio.google.com/app/apikeys")
    print()
    print("2. Inicie a aplicação com um dos comandos:")
    
    if sys.platform == "win32":
        print("   • Duplo clique em: run.bat")
        print("   • Ou no terminal: python -m streamlit run app.py")
    else:
        print("   • ./run.sh")
        print("   • Ou no terminal: python -m streamlit run app.py")
    
    print()
    print("3. A aplicação abrirá em: http://localhost:8502")
    print()
    print(f"{Colors.BOLD}Para futuras instalações em outros computadores:{Colors.ENDC}")
    print("• Clone o repositório git")
    print("• Execute 'python setup.py' novamente")
    print("• O script detectará automaticamente seus backups e oferecerá restaurá-los")
    print()

def main():
    os.chdir(Path(__file__).parent)
    
    print_header("BEM-VINDO AO AGENTE FINANCEIRO 💰")
    print("Setup Automático - Primeira Inicialização")
    print()
    
    try:
        print_header("VERIFICAÇÕES INICIAIS")
        check_python()
        check_pip()
        
        print_header("PREPARAÇÂO DO AMBIENTE")
        create_venv()
        install_dependencies()
        
        print_header("CONFIGURAÇÃO")
        setup_env()
        
        # Restaurar dados se disponível
        if find_backups():
            restore_backup()
        
        # Inicializar BD
        init_database()
        
        # Criar scripts de inicialização
        create_startup_script()
        
        print_next_steps()
        
    except KeyboardInterrupt:
        print_error("\nInstalação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erro durante instalação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
