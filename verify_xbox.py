import sqlite3

conn = sqlite3.connect("financeiro.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== VERIFICAÇÃO DETALHADA DE XBOX ===\n")

# Pegar o Xbox mais comum/barato
cursor.execute("""
    SELECT p.id, p.name, p.price, COALESCE(SUM(sm.quantity), 0) as total_stock
    FROM products p
    LEFT JOIN stock_movements sm ON p.id = sm.product_id
    WHERE LOWER(p.name) LIKE '%xbox%'
    GROUP BY p.id
    HAVING total_stock > 0
    ORDER BY total_stock DESC, p.price ASC
    LIMIT 1
""")

xbox = cursor.fetchone()

if xbox:
    product_id = xbox['id']
    name = xbox['name']
    price = xbox['price']
    total_stock = xbox['total_stock']
    
    print(f"Produto encontrado: {name}")
    print(f"ID: {product_id}")
    print(f"Preço: R$ {price:.2f}")
    print(f"Quantidade em estoque: {total_stock}")
    
    # Mostrar histórico de movimentações
    print(f"\n--- Histórico de movimentações do produto ---")
    cursor.execute("""
        SELECT id, quantity, movement_type, notes, created_at
        FROM stock_movements
        WHERE product_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (product_id,))
    
    movements = cursor.fetchall()
    if movements:
        for m in movements:
            print(f"  {m['created_at']}: {m['movement_type']:6} | Qtd: {m['quantity']:3} | Notas: {m['notes']}")
    else:
        print("  Nenhuma movimentação encontrada")
    
    # Verificar se há vendas registradas para este produto
    print(f"\n--- Vendas registradas ---")
    cursor.execute("""
        SELECT id, quantity, sale_date, status
        FROM sales
        WHERE product_id = ?
        ORDER BY sale_date DESC
        LIMIT 5
    """, (product_id,))
    
    sales = cursor.fetchall()
    if sales:
        for s in sales:
            print(f"  {s['sale_date']}: {s['quantity']} unidades | Status: {s['status']}")
    else:
        print("  Nenhuma venda registrada")
        
else:
    print("Nenhum Xbox disponível encontrado!")

conn.close()
