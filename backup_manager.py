#!/usr/bin/env python3
"""
Gerenciador de Backup - Agente Financeiro
Facilita backup, restauração e gerenciamento de dados
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from backup_utils import export_backup, import_backup

class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.metadata_file = self.backup_dir / "backups.json"
    
    def create_backup(self, description: str = ""):
        """Cria novo backup com descrição"""
        print("\n📦 Criando backup...")
        
        try:
            content, filename = export_backup()
            
            if content is None:
                print(f"❌ Erro: {filename}")
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / f"{timestamp}_{filename}"
            
            # Salvar arquivo
            if isinstance(content, bytes):
                with open(backup_path, 'wb') as f:
                    f.write(content)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Registrar metadados
            self.add_metadata(backup_path, description)
            
            print(f"✅ Backup criado: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar backup: {e}")
            return False
    
    def list_backups(self):
        """Lista todos os backups disponíveis"""
        backups = list(self.backup_dir.glob("*_backup*"))
        
        if not backups:
            print("Nenhum backup encontrado em /backups")
            return []
        
        print("\n📋 Backups disponíveis:\n")
        for i, backup in enumerate(sorted(backups, reverse=True), 1):
            size_mb = backup.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"[{i}] {backup.name}")
            print(f"    Tamanho: {size_mb:.2f}MB | Data: {mod_time}\n")
        
        return backups
    
    def restore_backup(self, backup_path: Path):
        """Restaura um backup específico"""
        print(f"\n♻️  Restaurando: {backup_path.name}...")
        
        try:
            with open(backup_path, 'rb') as f:
                content = f.read()
            
            success, message = import_backup(content)
            if success:
                print(f"✅ {message}")
                return True
            else:
                print(f"❌ {message}")
                return False
        except Exception as e:
            print(f"❌ Erro ao restaurar: {e}")
            return False
    
    def add_metadata(self, backup_path: Path, description: str = ""):
        """Registra metadados do backup"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            metadata[backup_path.name] = {
                "created": datetime.now().isoformat(),
                "description": description,
                "size_mb": backup_path.stat().st_size / (1024 * 1024)
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Aviso: Não consegui salvar metadados: {e}")
    
    def interactive_menu(self):
        """Menu interativo para gerenciar backups"""
        while True:
            print("\n" + "="*50)
            print("  GERENCIADOR DE BACKUPS - Agente Financeiro")
            print("="*50)
            print("\n[1] Criar novo backup")
            print("[2] Listar backups")
            print("[3] Restaurar backup")
            print("[4] Sair")
            
            choice = input("\nEscolha uma opção (1-4): ").strip()
            
            if choice == '1':
                desc = input("Descrição do backup (opcional): ").strip()
                self.create_backup(desc)
                input("\nPressione Enter para continuar...")
            
            elif choice == '2':
                backups = self.list_backups()
                input("Pressione Enter para continuar...")
            
            elif choice == '3':
                backups = self.list_backups()
                if backups:
                    try:
                        idx = int(input("Escolha o número do backup: ")) - 1
                        if 0 <= idx < len(backups):
                            confirm = input("Tem certeza? Isso sobrescreverá os dados atuais (s/n): ")
                            if confirm.lower() == 's':
                                self.restore_backup(backups[idx])
                    except ValueError:
                        print("Opção inválida!")
                input("\nPressione Enter para continuar...")
            
            elif choice == '4':
                print("Saindo...")
                break
            else:
                print("Opção inválida!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Gerenciador de Backups - Agente Financeiro')
    parser.add_argument('--create', action='store_true', help='Criar novo backup')
    parser.add_argument('--list', action='store_true', help='Listar backups')
    parser.add_argument('--restore', type=str, help='Restaurar um backup pelo caminho')
    parser.add_argument('--interactive', '-i', action='store_true', help='Menu interativo')
    parser.add_argument('--desc', type=str, default='', help='Descrição do backup')
    
    args = parser.parse_args()
    manager = BackupManager()
    
    if args.create:
        manager.create_backup(args.desc)
    elif args.list:
        manager.list_backups()
    elif args.restore:
        manager.restore_backup(Path(args.restore))
    elif args.interactive or not any([args.create, args.list, args.restore]):
        manager.interactive_menu()

if __name__ == "__main__":
    main()
