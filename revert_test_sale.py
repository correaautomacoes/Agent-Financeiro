import sqlite3, pathlib
p=pathlib.Path('financeiro.db')
conn=sqlite3.connect(p)
conn.row_factory = sqlite3.Row
cur=conn.cursor()
# IDs known from previous run
tx_id = 393
in_mv_id = 274
print('Transaction exists:', bool(cur.execute('SELECT 1 FROM transactions WHERE id = ?', (tx_id,)).fetchone()))
print('In movement exists:', bool(cur.execute('SELECT 1 FROM stock_movements WHERE id = ?', (in_mv_id,)).fetchone()))
# Find candidate out movements for product 91 after the in movement
cur.execute('''SELECT id,movement_type,quantity,reference FROM stock_movements WHERE product_id = ? AND movement_type='out' ORDER BY id DESC LIMIT 10''', (91,))
outs = cur.fetchall()
print('Recent out movements for product 91:')
for r in outs:
    print(dict(r))
# Heuristic: choose the most recent out movement with id > in_mv_id
out_id = None
for r in outs:
    if r['id'] > in_mv_id:
        out_id = r['id']
        break
print('Selected out_id to remove:', out_id)
# Show transaction row
if tx_id and cur.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,)).fetchone():
    row = cur.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,)).fetchone()
    print('Transaction row:', dict(row))
# Confirm and delete
if out_id:
    print('Deleting stock_movements id', out_id)
    cur.execute('DELETE FROM stock_movements WHERE id = ?', (out_id,))
else:
    print('No out movement selected; skipping stock_movements deletion')
if tx_id:
    print('Deleting transaction id', tx_id)
    cur.execute('DELETE FROM transactions WHERE id = ?', (tx_id,))
conn.commit()
# Final stock level
cur.execute("SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN quantity ELSE -quantity END),0) AS qty FROM stock_movements WHERE product_id = ?", (91,))
print('Final stock level for product 91:', cur.fetchone()['qty'])
conn.close()
