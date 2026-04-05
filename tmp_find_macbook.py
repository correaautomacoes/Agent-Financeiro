import sqlite3
conn=sqlite3.connect('financeiro.db')
cur=conn.cursor()
q="SELECT id, date, amount, category, description FROM transactions WHERE LOWER(COALESCE(description, '')) LIKE '%macbook%' OR LOWER(COALESCE(category, '')) LIKE '%infra%' ORDER BY date DESC LIMIT 20"
cur.execute(q)
rows=cur.fetchall()
print(rows)
conn.close()
