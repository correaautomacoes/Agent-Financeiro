import os
import subprocess
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()
DB_NAME = os.getenv("DB_NAME", "financial_db")
DB_USER = os.getenv("DB_USER", "admin")
SQLITE_PATH = os.getenv("SQLITE_PATH", "financeiro.db")

def export_backup():
    """
    Gera um backup do banco de dados (SQL para Postgres ou arquivo puro para SQLite).
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if DB_TYPE == "sqlite":
        filename = f"backup_lite_{timestamp}.db"
        try:
            if os.path.exists(SQLITE_PATH):
                with open(SQLITE_PATH, "rb") as f:
                    content = f.read()
                return content, filename
            else:
                return None, "Arquivo de banco SQLite não encontrado."
        except Exception as e:
            return None, str(e)
    else:
        # Modo Postgres / Docker
        filename = f"backup_pg_{timestamp}.sql"
        try:
            command = f"docker exec -t postgres pg_dump -U {DB_USER} {DB_NAME}"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout, filename
            else:
                return None, result.stderr
        except Exception as e:
            return None, str(e)

def import_backup(content):
    """
    Restaura um backup. Para SQLite espera bytes/arquivo, para Postgres espera SQL string.
    """
    try:
        if DB_TYPE == "sqlite":
            # Para restaurar SQLite, simplesmente sobrescrevemos o arquivo .db
            # Importante: O app pode precisar ser reiniciado para refletir mudanças se as conexões estiverem abertas
            with open(SQLITE_PATH, "wb") as f:
                if isinstance(content, str):
                    f.write(content.encode('utf-8')) # Caso venha como string por erro
                else:
                    f.write(content)
            return True, "Banco de dados local restaurado com sucesso! Reinicie o app se necessário."
        else:
            # Modo Postgres
            temp_file = "temp_restore.sql"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            input_file = os.path.abspath(temp_file)
            command = f"type {input_file} | docker exec -i postgres psql -U {DB_USER} -d {DB_NAME}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if os.path.exists(temp_file): os.remove(temp_file)
                
            if result.returncode == 0:
                return True, "Restauração Postgres concluída com sucesso!"
            else:
                return False, result.stderr
    except Exception as e:
        return False, str(e)
