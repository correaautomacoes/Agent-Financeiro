import sqlite3, json

conn = sqlite3.connect('financeiro_dev.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== CATEGORIAS AGRUPADAS ===")
cur.execute("SELECT type, category, COUNT(*) as cnt FROM transactions GROUP BY type, category ORDER BY type, cnt DESC")
print(json.dumps([dict(r) for r in cur.fetchall()], indent=2, ensure_ascii=False))

print("\n=== ÚLTIMAS 25 TRANSAÇÕES ===")
cur.execute("SELECT id, type, category, description, amount, date FROM transactions ORDER BY id DESC LIMIT 25")
print(json.dumps([dict(r) for r in cur.fetchall()], indent=2, ensure_ascii=False))

print("\n=== TIPOS DE DESPESA ===")
cur.execute("SELECT * FROM expense_types")
print(json.dumps([dict(r) for r in cur.fetchall()], indent=2, ensure_ascii=False))

print("\n=== TIPOS DE RECEITA ===")
cur.execute("SELECT * FROM income_types")
print(json.dumps([dict(r) for r in cur.fetchall()], indent=2, ensure_ascii=False))

conn.close()
