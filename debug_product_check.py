import sqlite3, pathlib, json
p=pathlib.Path('financeiro.db')
conn=sqlite3.connect(p)
conn.row_factory = sqlite3.Row
cur=conn.cursor()
# Buscar produto com 'Xbox' no nome (ou listar os 5 últimos produtos)
cur.execute("SELECT id,name,price,sku FROM products WHERE name LIKE '%Xbox%' LIMIT 5")
rows=cur.fetchall()
print('found_products:', len(rows))
for r in rows:
    print(dict(r))
    pid=r['id']
    # stock level
    cur.execute("SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN quantity ELSE -quantity END),0) AS qty FROM stock_movements WHERE product_id = ?",(pid,))
    print('stock_level:', cur.fetchone()[0])
    cur.execute("SELECT id,movement_type,quantity,unit_cost,reference,source,is_paid FROM stock_movements WHERE product_id=? ORDER BY id DESC LIMIT 10",(pid,))
    mv=cur.fetchall()
    print('last_movements:')
    for x in mv:
        print(dict(x))
    print('---')
# If no 'Xbox' product found, show last 5 products
if not rows:
    cur.execute('SELECT id,name,price FROM products ORDER BY id DESC LIMIT 5')
    for r in cur.fetchall():
        print('recent:', dict(r))
conn.close()
