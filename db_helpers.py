"""Helpers de banco de dados: CRUD para companies, partners, products, estoque e movimentos.

Use `python database.py` antes para garantir que as tabelas existam.
"""
from typing import Optional, List, Dict, Any
from database import get_db_connection, run_query


def create_company(name: str) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO companies (name) VALUES (%s) RETURNING id", (name,))
        company_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return company_id
    except Exception as e:
        print(f"Erro create_company: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None


def get_companies() -> List[Dict[str, Any]]:
    res = run_query("SELECT * FROM companies ORDER BY id DESC")
    return res or []


def create_partner(company_id: int, name: str, share_pct: float = 0.0) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO partners (company_id, name, share_pct) VALUES (%s, %s, %s) RETURNING id",
            (company_id, name, share_pct),
        )
        partner_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return partner_id
    except Exception as e:
        print(f"Erro create_partner: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None


def get_partners(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if company_id:
        res = run_query("SELECT * FROM partners WHERE company_id = %s ORDER BY id DESC", (company_id,))
    else:
        res = run_query("SELECT * FROM partners ORDER BY id DESC")
    return res or []


def create_product(company_id: int, name: str, price: float = 0.0, sku: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (company_id, sku, name, price) VALUES (%s, %s, %s, %s) RETURNING id",
            (company_id, sku, name, price),
        )
        product_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return product_id
    except Exception as e:
        print(f"Erro create_product: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None


def get_products(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if company_id:
        res = run_query("SELECT * FROM products WHERE company_id = %s ORDER BY id DESC", (company_id,))
    else:
        res = run_query("SELECT * FROM products ORDER BY id DESC")
    return res or []


def update_product(product_id: int, fields: Dict[str, Any]) -> bool:
    if not fields:
        return False
    keys = []
    vals = []
    for k, v in fields.items():
        keys.append(f"{k} = %s")
        vals.append(v)
    vals.append(product_id)
    query = f"UPDATE products SET {', '.join(keys)} WHERE id = %s"
    res = run_query(query, tuple(vals))
    return res is True


def delete_product(product_id: int) -> bool:
    res = run_query("DELETE FROM products WHERE id = %s", (product_id,))
    return res is True


def add_stock_movement(product_id: int, quantity: int, movement_type: str, reference: Optional[str] = None, source: str = 'próprio', is_paid: bool = False, unit_cost: float = 0.0) -> Optional[int]:
    if movement_type not in ("in", "out"):
        print("movement_type must be 'in' or 'out'")
        return None
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stock_movements (product_id, quantity, movement_type, reference, source, is_paid) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (product_id, quantity, movement_type, reference, source, is_paid),
        )
        mid = cur.fetchone()[0]

        # Se for entrada paga, gera uma despesa automática no financeiro
        if movement_type == 'in' and is_paid and unit_cost > 0:
            total_cost = unit_cost * quantity
            cur.execute(
                "INSERT INTO transactions (type, amount, category, description, date, product_id) VALUES (%s, %s, %s, %s, CURRENT_DATE, %s)",
                ('Despesa', total_cost, 'Estoque/Compra', f"Compra de estoque: {reference}", product_id)
            )

        conn.commit()
        cur.close()
        conn.close()
        return mid
    except Exception as e:
        print(f"Erro add_stock_movement: {e}")
        try: conn.rollback()
        except: pass
        conn.close()
        return None


def get_stock_level(product_id: int) -> int:
    res = run_query(
        "SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN quantity WHEN movement_type='out' THEN -quantity END),0) AS qty FROM stock_movements WHERE product_id = %s",
        (product_id,),
    )
    if res and isinstance(res, list) and len(res) > 0:
        return int(res[0].get("qty", 0))
    return 0


def create_contribution(partner_id: int, amount: float, date: Optional[str] = None, note: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO contributions (partner_id, amount, date, note) VALUES (%s, %s, %s, %s) RETURNING id",
            (partner_id, amount, date, note),
        )
        cid = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return cid
    except Exception as e:
        print(f"Erro create_contribution: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None


def create_withdrawal(partner_id: int, amount: float, date: Optional[str] = None, reason: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO withdrawals (partner_id, amount, date, reason) VALUES (%s, %s, %s, %s) RETURNING id",
            (partner_id, amount, date, reason),
        )
        wid = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return wid
    except Exception as e:
        print(f"Erro create_withdrawal: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None


def get_expense_types(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if company_id:
        res = run_query("SELECT * FROM expense_types WHERE company_id = %s ORDER BY id", (company_id,))
    else:
        res = run_query("SELECT * FROM expense_types ORDER BY id")
    return res or []


def get_income_types(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if company_id:
        res = run_query("SELECT * FROM income_types WHERE company_id = %s ORDER BY id", (company_id,))
    else:
        res = run_query("SELECT * FROM income_types ORDER BY id")
    return res or []


def create_sale(product_id: int, quantity: int, unit_price: float, company_id: Optional[int] = None, partner_id: Optional[int] = None, description: Optional[str] = None) -> Optional[int]:
    """Registra uma venda: verifica estoque, insere movimento 'out' e cria uma transaction do tipo 'Receita'.

    Retorna id da transação criada ou None em caso de erro.
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()

        # Verifica estoque atual
        cur.execute(
            "SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN quantity WHEN movement_type='out' THEN -quantity END),0) AS qty FROM stock_movements WHERE product_id = %s",
            (product_id,),
        )
        row = cur.fetchone()
        available = int(row[0]) if row and row[0] is not None else 0
        if available < quantity:
            raise Exception(f"Estoque insuficiente (disponível={available}, requisitado={quantity})")

        # Inserir movimento de saída
        cur.execute(
            "INSERT INTO stock_movements (product_id, quantity, movement_type, reference) VALUES (%s, %s, %s, %s) RETURNING id",
            (product_id, quantity, 'out', description),
        )
        stock_id = cur.fetchone()[0]

        # Criar transaction de venda
        total = float(unit_price) * int(quantity)
        cur.execute(
            "INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, %s, %s) RETURNING id",
            ('Receita', total, 'Venda', description, product_id, partner_id, company_id),
        )
        trans_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()
        return trans_id
    except Exception as e:
        print(f"Erro create_sale: {e}")
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return None

def get_partner_reports(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Calcula o lucro acumulado por sócio baseado na % de participação e subtrai as retiradas."""
    query = """
    WITH partner_data AS (
        SELECT 
            p.id, 
            p.name, 
            p.share_pct,
            -- Soma de todas as receitas da empresa
            COALESCE((SELECT SUM(amount) FROM transactions WHERE type='Receita' AND company_id = p.company_id), 0) AS total_revenue,
            -- Soma de todas as despesas da empresa
            COALESCE((SELECT SUM(amount) FROM transactions WHERE type='Despesa' AND company_id = p.company_id), 0) AS total_expenses,
            -- Total de retiradas desse sócio
            COALESCE((SELECT SUM(amount) FROM withdrawals WHERE partner_id = p.id), 0) AS total_withdrawn,
            -- Total de aportes desse sócio
            COALESCE((SELECT SUM(amount) FROM contributions WHERE partner_id = p.id), 0) AS total_contributed
        FROM partners p
    )
    SELECT 
        *,
        (total_revenue - total_expenses) * (share_pct / 100.0) AS share_of_profit,
        ((total_revenue - total_expenses) * (share_pct / 100.0)) - total_withdrawn AS current_balance
    FROM partner_data
    """
    if company_id:
        query += f" WHERE company_id = {company_id}"
    
    return run_query(query) or []

def get_advanced_kpis(period: str = 'month'):
    """Retorna KPIs filtrados por período (week, month, year)."""
    filter_sql = "1=1"
    if period == 'week': filter_sql = "date >= CURRENT_DATE - INTERVAL '7 days'"
    elif period == 'month': filter_sql = "EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif period == 'year': filter_sql = "EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)"

    query = f"""
    SELECT 
        COALESCE(SUM(CASE WHEN type='Receita' THEN amount ELSE 0 END), 0) AS revenue,
        COALESCE(SUM(CASE WHEN type='Despesa' THEN amount ELSE 0 END), 0) AS expenses,
        COALESCE(SUM(CASE WHEN type='Receita' THEN amount ELSE -amount END), 0) AS net_profit
    FROM transactions
    WHERE {filter_sql}
    """
    return run_query(query)

def get_upcoming_alerts():
    """Busca despesas fixas próximas do vencimento."""
    query = """
    SELECT * FROM fixed_expenses 
    WHERE due_day >= EXTRACT(DAY FROM CURRENT_DATE) 
    AND due_day <= EXTRACT(DAY FROM CURRENT_DATE) + 5
    """
    return run_query(query) or []

def create_fixed_expense(company_id: int, name: str, amount: float, due_day: int):
    """Cria uma nova despesa fixa agendada."""
    query = """
    INSERT INTO fixed_expenses (company_id, name, amount, due_day)
    VALUES (%s, %s, %s, %s)
    """
    return run_query(query, (company_id, name, amount, due_day))

def get_inventory_report():
    """Retorna o resumo do estoque, quantidades e valor total por produto."""
    query = """
    SELECT 
        p.id, 
        p.name, 
        p.price,
        COALESCE(SUM(CASE WHEN m.movement_type='in' THEN m.quantity WHEN m.movement_type='out' THEN -m.quantity END), 0) as stock_qty,
        (p.price * COALESCE(SUM(CASE WHEN m.movement_type='in' THEN m.quantity WHEN m.movement_type='out' THEN -m.quantity END), 0)) as total_value
    FROM products p
    LEFT JOIN stock_movements m ON p.id = m.product_id
    GROUP BY p.id, p.name, p.price
    """
    return run_query(query) or []

def get_revenue_details():
    """Separa as receitas por 'Venda de Produto' e 'Prestação de Serviço'."""
    query = """
    SELECT 
        CASE WHEN product_id IS NOT NULL THEN 'Venda de Produto' ELSE 'Prestação de Serviço' END as channel,
        SUM(amount) as total
    FROM transactions
    WHERE type = 'Receita'
    GROUP BY 1
    """
    return run_query(query) or []
