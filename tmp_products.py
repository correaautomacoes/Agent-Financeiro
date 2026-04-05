import sqlite3
c = sqlite3.connect('financeiro.db')
cur = c.cursor()
cur.execute("SELECT id,name,price FROM products WHERE LOWER(name) LIKE '%macbook%'")
print(cur.fetchall())
c.close()
