import sqlite3
from db_helpers import add_stock_movement

conn = sqlite3.connect('financeiro.db')
cur = conn.cursor()
cur.execute("UPDATE transactions SET category='Estoque/Compra' WHERE id=125")
conn.commit()

mid = add_stock_movement(3, 1, 'in', reference='Movimentacao gerada de infra para estoque', source='ajuste', is_paid=True, unit_cost=800)
print('stock_movement_id=', mid)
conn.close()
