import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuração de Tipo de Banco (sqlite ou postgres)
DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()

# Configurações Postgres
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financial_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin_password")

# Configurações SQLite
SQLITE_PATH = os.getenv("SQLITE_PATH", "financeiro.db")

def get_db_connection():
    try:
        if DB_TYPE == "sqlite":
            conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row # Para retornar como dicionário
            return conn
        else:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            return conn
    except Exception as e:
        print(f"Error connecting to database ({DB_TYPE}): {e}")
        raise e

def run_query(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            # Tradução de sintaxe básica para compatibilidade cross-DB
            if DB_TYPE == "sqlite" and params:
                query = query.replace("%s", "?")
            
            if DB_TYPE == "sqlite":
                cur = conn.cursor()
                cur.execute(query, params or ())
                
                if cur.description:
                    # Converte sqlite3.Row para lista de dicionários
                    result = [dict(row) for row in cur.fetchall()]
                else:
                    conn.commit()
                    result = True
            else:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(query, params)
                if cur.description:
                    result = cur.fetchall()
                else:
                    conn.commit()
                    result = True
            
            cur.close()
            conn.close()
            return result
        except Exception as e:
            print(f"Error executing query on {DB_TYPE}: {e}")
            try: conn.rollback()
            except: pass
            conn.close()
            raise e
    return None

def save_transactions_batch(df):
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        placeholder = "?" if DB_TYPE == "sqlite" else "%s"
        insert_query = f"""
        INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                row.get('type'),
                float(row.get('amount') or 0),
                row.get('category'),
                row.get('description'),
                str(row.get('date')),
                row.get('product_id'),
                row.get('partner_id'),
                row.get('company_id')
            ))
        cur.executemany(insert_query, data_to_insert)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar lote: {e}")
        if conn:
            try: conn.rollback()
            except: pass
            conn.close()
        return False

def init_db():
    # Traduzir sintaxe SERIAL/PRIMARY KEY para ser compatível
    # SQLite usa AUTOINCREMENT, Postgres usa SERIAL
    serial_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if DB_TYPE == "sqlite" else "SERIAL PRIMARY KEY"
    
    # Scripts compatíveis
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS companies (
        id {serial_type},
        name VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS partners (
        id {serial_type},
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        share_pct DECIMAL(5,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS expense_types (
        id {serial_type},
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS income_types (
        id {serial_type},
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id {serial_type},
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        sku VARCHAR(100),
        name VARCHAR(255) NOT NULL,
        price DECIMAL(12,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        id {serial_type},
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        movement_type VARCHAR(10) NOT NULL,
        reference TEXT,
        source VARCHAR(50) DEFAULT 'próprio',
        is_paid BOOLEAN DEFAULT FALSE,
        unit_cost DECIMAL(12,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS contributions (
        id {serial_type},
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        amount DECIMAL(12,2) NOT NULL,
        date DATE DEFAULT CURRENT_DATE,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS withdrawals (
        id {serial_type},
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        amount DECIMAL(12,2) NOT NULL,
        date DATE DEFAULT CURRENT_DATE,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS fixed_expenses (
        id {serial_type},
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        amount DECIMAL(12,2) NOT NULL,
        due_day INTEGER,
        start_date DATE,
        end_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id {serial_type},
        type VARCHAR(20) NOT NULL,
        amount DECIMAL(12, 2) NOT NULL,
        category VARCHAR(100),
        description TEXT,
        date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL
    );
    """
    
    # Executar as criações individualmente se for SQLite (ele prefere) ou tudo junto no postgres
    if DB_TYPE == "sqlite":
        for statement in create_table_query.split(';'):
            if statement.strip():
                run_query(statement)
    else:
        run_query(create_table_query)
    
    # Migrações rápidas para Postgres
    try:
        if DB_TYPE == "postgres":
            run_query("ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'próprio'")
            run_query("ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE")
            run_query("ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS unit_cost DECIMAL(12,2) DEFAULT 0")
    except: pass

    print(f"Banco de dados ({DB_TYPE}) inicializado com sucesso!")

if __name__ == "__main__":
    init_db()
