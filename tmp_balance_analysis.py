import sqlite3

conn = sqlite3.connect('financeiro.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('tables:')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(row[0])

print('--- transactions summary ---')
for row in cur.execute("SELECT type, COALESCE(SUM(amount),0) AS total, COUNT(*) AS count FROM transactions GROUP BY type"):
    print(row['type'], row['total'], row['count'])

print('--- contributions/withdrawals ---')
for row in cur.execute("SELECT 'contributions' AS table_name, COALESCE(SUM(amount),0) AS total, COUNT(*) AS count FROM contributions UNION ALL SELECT 'withdrawals', COALESCE(SUM(amount),0), COUNT(*) FROM withdrawals"):
    print(row['table_name'], row['total'], row['count'])

print('--- receivables summary ---')
for row in cur.execute("SELECT status, COALESCE(SUM(amount),0) AS total, COALESCE(SUM(paid_amount),0) AS paid, COUNT(*) AS cnt FROM receivables GROUP BY status"):
    print(row['status'], row['total'], row['paid'], row['cnt'])

print('--- accounts_receivable summary ---')
for row in cur.execute("SELECT status, COALESCE(SUM(total_amount),0) AS total, COALESCE(SUM(received_amount),0) AS paid, COUNT(*) AS cnt FROM accounts_receivable GROUP BY status"):
    print(row['status'], row['total'], row['paid'], row['cnt'])

print('--- fixed expenses ---')
for row in cur.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS total FROM fixed_expenses"):
    print(row['cnt'], row['total'])

print('--- stock movements ---')
for row in cur.execute("SELECT movement_type, COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(quantity*unit_cost),0) AS cost FROM stock_movements GROUP BY movement_type"):
    print(row['movement_type'], row['qty'], row['cost'])

print('--- products ---')
for row in cur.execute("SELECT COUNT(*) AS cnt FROM products"):
    print(row['cnt'])

print('--- partners ---')
for row in cur.execute("SELECT COUNT(*) AS cnt FROM partners"):
    print(row['cnt'])

print('--- current cash according app logic ---')
for row in cur.execute("SELECT (SELECT COALESCE(SUM(CASE WHEN type='Receita' AND COALESCE(category,'') = 'Venda a Prazo' THEN 0 WHEN type='Receita' THEN amount ELSE -amount END),0) FROM transactions) + (SELECT COALESCE(SUM(amount),0) FROM contributions) - (SELECT COALESCE(SUM(amount),0) FROM withdrawals) AS total_cash"):
    print(row['total_cash'])

print('--- receivable open amount app logic ---')
for row in cur.execute("SELECT COALESCE(SUM(CASE WHEN status='pending' THEN amount-COALESCE(paid_amount,0) ELSE 0 END),0) AS pending_total FROM receivables"):
    print(row['pending_total'])

conn.close()
