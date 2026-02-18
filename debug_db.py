import database
import json

def debug_insert():
    t = {
        "type": "Despesa",
        "amount": 30.0,
        "category": "Transporte",
        "description": "Gasolina",
        "date": "2026-02-18"
    }
    
    query = """
    INSERT INTO transactions (type, amount, category, description, date)
    VALUES (%s, %s, %s, %s, %s)
    """
    params = (t["type"], t["amount"], t["category"], t["description"], t["date"])
    
    conn = database.get_db_connection()
    if not conn:
        print("ERRO: Não conseguiu conectar.")
        return
        
    try:
        cur = conn.cursor()
        print(f"Executando query: {query}")
        print(f"Com params: {params}")
        cur.execute(query, params)
        conn.commit()
        print("✅ Inserção bem-sucedida no script de debug!")
    except Exception as e:
        print(f"❌ ERRO REAL DO POSTGRES: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    debug_insert()
