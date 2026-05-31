from db_helpers import create_sale
print('Calling create_sale...')
res = create_sale(product_id=91, quantity=1, unit_price=750, description='Venda teste', payment_mode='avista')
print('Result:', res)
