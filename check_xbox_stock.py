import sqlite3

conn = sqlite3.connect("financeiro.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== VERIFICAÇÃO DE XBOX DISPONÍVEL ===\n")

# Buscar um Xbox
cursor.execute("""
    SELECT p.id, p.name, p.price
    FROM products p
    WHERE LOWER(p.name) LIKE '%xbox%'
    LIMIT 1
""")

xbox = cursor.fetchone()

if xbox:
    product_id = xbox['id']
    name = xbox['name']
    price = xbox['price']
    
    print(f"Produto: {name}")
    print(f"ID: {product_id}")
    print(f"Preço: R$ {price:.2f}")
    
    # Verificar estoque deste produto
    cursor.execute("""
        SELECT id, quantity, movement_type, created_at
        FROM stock_movements
        WHERE product_id = ?
        ORDER BY created_at
    """, (product_id,))
    
    movements = cursor.fetchall()
    total_stock = sum([m['quantity'] for m in movements])
    
    print(f"\nMovimentações de estoque:")
    for m in movements:
        print(f"  ID {m['id']}: {m['movement_type']:6} | Qtd: {m['quantity']:3} | Data: {m['created_at']}")
    
    print(f"\nEstoque total calculado: {total_stock} unidades")
    
    if total_stock > 0:
        print(f"\n✓ SIM! Tem {total_stock} unidade(s) de '{name}' disponível(is)!")
    else:
        print(f"\n✗ NÃO tem estoque deste produto")
else:
    print("Nenhum Xbox encontrado")

conn.close()
