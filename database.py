import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(override=True)

# Ler configurações do .env com valores padrão
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financial_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin_password")


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise e # Propaga o erro para ser capturado pela UI


def run_query(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            
            # Se a query retorna resultados (SELECT, WITH ... SELECT, RETURNING), buscamos os dados
            if cur.description:
                result = cur.fetchall()
            else:
                conn.commit()
                result = True
            cur.close()
            conn.close()
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            try:
                conn.rollback()
            except:
                pass
            conn.close()
            raise e # Propaga o erro para ser capturado pela UI
    return None


def save_transactions_batch(df):
    """
    Salva um DataFrame de transações no banco de dados.
    Espera colunas: type, amount, category, description, date
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                row.get('type'),
                float(row.get('amount') or 0),
                row.get('category'),
                row.get('description'),
                row.get('date'),
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
            try:
                conn.rollback()
            except:
                pass
            conn.close()
        return False


def init_db():
    """
    Cria as tabelas iniciais necessárias para o sistema financeiro ampliado.
    Executar `python database.py` para aplicar essas alterações.
    """
    create_table_query = """
    -- Empresas
    CREATE TABLE IF NOT EXISTS companies (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Sócios / parceiros
    CREATE TABLE IF NOT EXISTS partners (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        share_pct DECIMAL(5,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Tipos de despesa / receita
    CREATE TABLE IF NOT EXISTS expense_types (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS income_types (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL
    );

    -- Produtos
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        sku VARCHAR(100),
        name VARCHAR(255) NOT NULL,
        price DECIMAL(12,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Movimentações de estoque (entradas/saídas)
    CREATE TABLE IF NOT EXISTS stock_movements (
        id SERIAL PRIMARY KEY,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        movement_type VARCHAR(10) NOT NULL CHECK (movement_type IN ('in','out')),
        reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Participações e repasses (aportes/retiradas)
    CREATE TABLE IF NOT EXISTS contributions (
        id SERIAL PRIMARY KEY,
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        amount DECIMAL(12,2) NOT NULL,
        date DATE DEFAULT CURRENT_DATE,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS withdrawals (
        id SERIAL PRIMARY KEY,
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        amount DECIMAL(12,2) NOT NULL,
        date DATE DEFAULT CURRENT_DATE,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Despesas fixas
    CREATE TABLE IF NOT EXISTS fixed_expenses (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        amount DECIMAL(12,2) NOT NULL,
        due_day INTEGER,
        start_date DATE,
        end_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Extensão da tabela transactions (mantemos compatibilidade)
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        type VARCHAR(20) NOT NULL CHECK (type IN ('Receita', 'Despesa')),
        amount DECIMAL(12, 2) NOT NULL,
        category VARCHAR(100),
        description TEXT,
        date DATE NOT NULL DEFAULT CURRENT_DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
        partner_id INTEGER REFERENCES partners(id) ON DELETE SET NULL,
        company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL
    );

    -- Índices úteis
    CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
    CREATE INDEX IF NOT EXISTS idx_products_company ON products(company_id);
    """

    # Executa a criação das tabelas
    res = run_query(create_table_query)
    if res is None:
        print("Houve um erro ao criar as tabelas. Veja logs acima.")
    else:
        print("Migrações iniciais aplicadas com sucesso — tabelas verificadas/criadas.")


if __name__ == "__main__":
    init_db()
