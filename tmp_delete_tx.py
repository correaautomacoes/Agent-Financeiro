import sqlite3
conn=sqlite3.connect('financeiro.db')
cur=conn.cursor()
cur.execute('DELETE FROM transactions WHERE id=175')
conn.commit()
cur.execute('SELECT id,date,amount,category,description FROM transactions WHERE id=175')
print(cur.fetchall())
conn.close()
