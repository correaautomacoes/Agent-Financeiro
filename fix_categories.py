"""
Script para corrigir os lançamentos importados incorretamente.
Todos os 15 lançamentos estão com type='Receita' mas são Despesas.
Vamos corrigir baseado em palavras-chave comuns de despesa.
"""
import sqlite3

conn = sqlite3.connect('financeiro_dev.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Palavras-chave que indicam despesa
despesa_keywords = [
    'aluguel', 'compra', 'combustivel', 'combustível', 'alimentacao', 'alimentação',
    'adiantamento', 'vps', 'dominio', 'domínio', 'ssd', 'solda', 'insumo',
    'saque', 'retirada', 'custo', 'pagamento', 'bonder', 'infra', 'infraestrutura'
]

cur.execute("SELECT id, type, description, category FROM transactions")
rows = cur.fetchall()

corrigidos = 0
for row in rows:
    desc = (row['description'] or '').lower()
    cat = (row['category'] or '').lower()
    texto = desc + ' ' + cat
    
    if any(kw in texto for kw in despesa_keywords):
        cur.execute("UPDATE transactions SET type='Despesa' WHERE id=?", (row['id'],))
        print(f"[CORRIGIDO] ID={row['id']} | {row['description']} | {row['category']} -> Despesa")
        corrigidos += 1

conn.commit()
conn.close()
print(f"\nTotal corrigido: {corrigidos} registros.")
