import sqlite3

conn = sqlite3.connect("financeiro.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar produtos com Xbox
cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%xbox%', '%x box%'))
products = cursor.fetchall()

if products:
    print("=== Produtos com Xbox ===")
    for p in products:
        product_id = p['id']
        name = p['name']
        price = p['price']
        
        # Pegar quantidade em estoque
        cursor.execute("""
            SELECT COALESCE(SUM(quantity), 0) as total_stock
            FROM stock_movements
            WHERE product_id = ?
        """, (product_id,))
        stock = cursor.fetchone()
        total_stock = stock['total_stock'] if stock else 0
        
        print(f"\nProduto: {name}")
        print(f"  ID: {product_id}")
        print(f"  Preço: R$ {price:.2f}")
        print(f"  Estoque: {total_stock} unidades")
else:
    print("Nenhum produto Xbox encontrado no banco de dados")

# Mostrar todos os produtos disponíveis para referência
print("\n=== Todos os produtos com estoque disponível ===")
cursor.execute("""
    SELECT p.id, p.name, p.price, COALESCE(SUM(sm.quantity), 0) as total_stock
    FROM products p
    LEFT JOIN stock_movements sm ON p.id = sm.product_id
    GROUP BY p.id
    HAVING total_stock > 0
    ORDER BY total_stock DESC
""")
all_products = cursor.fetchall()

if all_products:
    for p in all_products:
        print(f"- {p['name']}: {p['total_stock']} unidades (R$ {p['price']:.2f})")
else:
    print("Nenhum produto com estoque disponível")

conn.close()
