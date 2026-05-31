from db_helpers import add_stock_movement, create_sale, get_stock_level
pid=91
print('Before stock level:', get_stock_level(pid))
mid = add_stock_movement(product_id=pid, quantity=1, movement_type='in', reference='Ajuste para teste', source='manual', is_paid=True, unit_cost=600)
print('Added stock movement id:', mid)
print('After stock level:', get_stock_level(pid))
res = create_sale(product_id=pid, quantity=1, unit_price=750, description='Venda teste após ajuste', payment_mode='avista')
print('create_sale result:', res)
print('Final stock level:', get_stock_level(pid))
