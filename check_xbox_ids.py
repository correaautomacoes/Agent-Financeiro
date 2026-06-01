import sqlite3

conn = sqlite3.connect('financeiro.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
for pid in (133, 134):
    cur.execute('SELECT id, name, price FROM products WHERE id=?', (pid,))
    p = cur.fetchone()
    if not p:
        continue
    cur.execute('SELECT COALESCE(SUM(quantity), 0) AS total_stock FROM stock_movements WHERE product_id=?', (pid,))
    stock = cur.fetchone()['total_stock']
    print(f'ID {p["id"]}: {p["name"]} - R$ {p["price"]:.2f} - Estoque: {stock}')
    cur.execute('SELECT id, quantity, movement_type, created_at FROM stock_movements WHERE product_id=? ORDER BY created_at', (pid,))
    for m in cur.fetchall():
        print(f'  mov {m["id"]}: {m["movement_type"]} {m["quantity"]} at {m["created_at"]}')
    print()
conn.close()
