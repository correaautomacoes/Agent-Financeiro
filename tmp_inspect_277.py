import sqlite3

conn = sqlite3.connect('financeiro.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

queries = [
    ('transactions', 'SELECT * FROM transactions WHERE id=277'),
    ('accounts_receivable_by_id', 'SELECT * FROM accounts_receivable WHERE id=277'),
    ('accounts_receivable_by_sale', 'SELECT * FROM accounts_receivable WHERE sale_transaction_id=277'),
    ('accounts_receivable_all', 'SELECT * FROM accounts_receivable LIMIT 20'),
]

for label, query in queries:
    print('---', label, '---')
    try:
        rows = cur.execute(query).fetchall()
        if not rows:
            print('NONE')
        for r in rows:
            print(dict(r))
    except Exception as e:
        print('ERROR:', e)

try:
    print('--- accounts_receivable count ---')
    print(cur.execute('SELECT count(*) FROM accounts_receivable').fetchone()[0])
except Exception as e:
    print('ERROR COUNT:', e)

conn.close()
