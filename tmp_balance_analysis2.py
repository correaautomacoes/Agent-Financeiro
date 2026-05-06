import sqlite3

conn = sqlite3.connect('financeiro.db')
cur = conn.cursor()

cur.execute("SELECT status, SUM(total_amount), SUM(received_amount), COUNT(*) FROM accounts_receivable GROUP BY status")
print('accounts_receivable status totals:')
for row in cur.fetchall():
    print(row)

cur.execute("SELECT SUM(total_amount - received_amount) FROM accounts_receivable WHERE total_amount - received_amount > 0")
print('accounts_receivable outstanding:', cur.fetchone()[0])

cur.execute("SELECT SUM(amount - COALESCE(paid_amount,0)) FROM receivables WHERE status != 'paid'")
print('receivables outstanding:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM receivables WHERE status != 'paid'")
print('receivables open count:', cur.fetchone()[0])

conn.close()
