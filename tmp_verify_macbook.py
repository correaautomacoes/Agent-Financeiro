import sqlite3
conn=sqlite3.connect('financeiro.db')
cur=conn.cursor()
cur.execute("SELECT id,date,amount,category,description FROM transactions WHERE id=125")
print(cur.fetchall())
cur.execute("SELECT product_id, quantity, unit_cost FROM stock_movements WHERE id=122")
print(cur.fetchall())
conn.close()
