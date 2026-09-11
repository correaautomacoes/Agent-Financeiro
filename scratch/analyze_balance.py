import sqlite3
import pandas as pd

conn = sqlite3.connect('financeiro.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== 1. LOANS IN DATABASE ===")
for r in cur.execute("SELECT * FROM partner_loans"):
    print(dict(r))

print("\n=== 2. LOAN TRANSACTIONS IN TRANSACTIONS TABLE ===")
for r in cur.execute("SELECT id, date, type, amount, category, description FROM transactions WHERE category LIKE '%Empr%' OR description LIKE '%LOAN%'"):
    print(dict(r))

print("\n=== 3. BANK ACCOUNTS ===")
for r in cur.execute("SELECT * FROM bank_accounts"):
    print(dict(r))

print("\n=== 4. AMORTIZATION PAYMENTS IN LOAN_INSTALLMENTS OR LOANS ===")
try:
    for r in cur.execute("SELECT * FROM partner_loan_installments"):
        print(dict(r))
except Exception as e:
    print("partner_loan_installments error:", e)

print("\n=== 5. CHECK ALL TRANSACTIONS DATES & TYPES ===")
df = pd.read_sql_query("SELECT id, date, type, amount, category, description FROM transactions ORDER BY date ASC, id ASC", conn)
print("Total rows:", len(df))
receitas = df[df['type'] == 'Receita']['amount'].sum()
despesas = df[df['type'] == 'Despesa']['amount'].sum()
print(f"Soma Receitas: {receitas:.2f}")
print(f"Soma Despesas: {despesas:.2f}")
print(f"Diferenca (Receitas - Despesas): {receitas - despesas:.2f}")

withdrawals = cur.execute("SELECT COALESCE(SUM(amount), 0) FROM withdrawals").fetchone()[0]
contributions = cur.execute("SELECT COALESCE(SUM(amount), 0) FROM contributions").fetchone()[0]
print(f"Soma Retiradas (withdrawals): {withdrawals:.2f}")
print(f"Soma Aportes (contributions): {contributions:.2f}")

saldo_caixa_total = (receitas - despesas) + contributions - withdrawals
print(f"Saldo Caixa Total (sem filtro): {saldo_caixa_total:.2f}")

conn.close()
