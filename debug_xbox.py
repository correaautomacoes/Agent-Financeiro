import sqlite3

try:
    conn = sqlite3.connect("financeiro.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tabelas no banco de dados:")
    for t in tables:
        print(f"  - {t['name']}")
    
    # Verificar se existe dados na tabela products
    cursor.execute("SELECT COUNT(*) as count FROM products")
    count = cursor.fetchone()
    print(f"\nTotal de produtos: {count['count']}")
    
    # Listar estrutura de stock_movements
    print("\nEstrututa de stock_movements:")
    cursor.execute("PRAGMA table_info(stock_movements)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['name']}: {col['type']}")
    
    # Verificar dados em stock_movements
    cursor.execute("SELECT COUNT(*) as count FROM stock_movements")
    count = cursor.fetchone()
    print(f"\nTotal de movimentações de estoque: {count['count']}")
    
    # Buscar um Xbox
    cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE '%xbox%' LIMIT 1")
    xbox = cursor.fetchone()
    if xbox:
        print(f"\nXbox encontrado: {xbox['name']} (ID: {xbox['id']})")
        
        # Verificar estoque deste produto
        cursor.execute("SELECT * FROM stock_movements WHERE product_id = ?", (xbox['id'],))
        movements = cursor.fetchall()
        print(f"Movimentações para este produto: {len(movements)}")
        for m in movements:
            print(f"  - Qtd: {m['quantity']}, Tipo: {m['movement_type']}, Data: {m.get('created_at', 'N/A')}")
    else:
        print("Nenhum Xbox encontrado")
    
    conn.close()
except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
