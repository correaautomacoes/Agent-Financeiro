import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import init_db
from db_helpers import get_advanced_kpis, get_partner_reports, get_all_bank_accounts, get_bank_account

sys.stdout.reconfigure(encoding='utf-8')

init_db()

k = get_advanced_kpis('month')[0]
print("=== ADVANCED KPIS ===")
print(f"Faturamento: R$ {k['revenue']:.2f}")
print(f"Despesas Operacionais: R$ {k['expenses']:.2f}")
print(f"CMV: R$ {k['cmv']:.2f}")
print(f"Lucro Bruto: R$ {k['gross_profit']:.2f}")
print(f"Lucro Líquido: R$ {k['net_profit']:.2f}")
print(f"Saldo em Caixa Real (total_cash): R$ {k['total_cash']:.2f}")

pr = get_partner_reports()[0]
print("\n=== PARTNER REPORTS ===")
print(f"Sócio: {pr['name']}")
print(f"Lucro Gerado: R$ {pr['share_of_profit']:.2f}")
print(f"Total Retirado: R$ {pr['total_withdrawn']:.2f}")
print(f"Saldo de Lucro: R$ {pr['available_balance']:.2f}")

assert round(k['net_profit'], 2) == round(pr['share_of_profit'], 2), f"Divergência: {k['net_profit']} vs {pr['share_of_profit']}"
print("\n>>> SUCESSO: Lucro Líquido do Dashboard e Lucro Gerado do Sócio estão 100% alinhados!")

print("\n=== BANK ACCOUNTS ===")
accounts = get_all_bank_accounts()
for a in accounts:
    print(dict(a))
