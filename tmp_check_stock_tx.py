import sqlite3
conn=sqlite3.connect('financeiro.db')
cur=conn.cursor()
cur.execute("SELECT id,date,amount,category,description FROM transactions WHERE category='Estoque/Compra' AND description LIKE 'Compra: Movimentacao gerada de infra para estoque%'")
rows=cur.fetchall()
print(rows)
conn.close()
