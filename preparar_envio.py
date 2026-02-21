import os
import shutil

def preparar_pacote():
    # Nome da pasta de destino
    destino = "../Agente_Financeiro_Pronto"
    
    # Arquivos e pastas permitidos
    permitidos = [
        "app.py",
        "ai_agent.py",
        "database.py",
        "db_helpers.py",
        "backup_utils.py",
        "instalar_windows.bat",
        "criar_atalho.ps1",
        "run_app.bat",
        "requirements.txt",
        "docker-compose.yaml",
        ".env.example",
        "README.md",
        "GUIA_INSTALACAO.md",
        ".gitignore",
        # Incluir outros arquivos de sistema se houver
        "app_import_snippet.py",
        "append_script.py",
        "debug_db.py",
        "test_models.py"
    ]

    # Criar pasta de destino se não existir
    if os.path.exists(destino):
        print(f"Limpando pasta antiga: {destino}")
        shutil.rmtree(destino)
    
    os.makedirs(destino)
    print(f"Criando pasta: {destino}")

    # Copiar arquivos
    for item in permitidos:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(destino, item))
                print(f"Pasta copiada: {item}")
            else:
                shutil.copy2(item, destino)
                print(f"Arquivo copiado: {item}")
        else:
            print(f"Aviso: Item '{item}' não encontrado. Pulando...")

    print("\n" + "="*40)
    print("PACOTE PRONTO PARA ENVIO!")
    print("="*40)
    print(f"Os arquivos foram copiados para: {os.path.abspath(destino)}")
    print("Agora você pode compactar (RAR/ZIP) essa pasta.")
    print("Lembre-se: O arquivo .env e a pasta venv foram EXCLUÍDOS com sucesso.")
    print("="*40)

if __name__ == "__main__":
    preparar_pacote()
