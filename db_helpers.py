from typing import Optional, List, Dict, Any
import os
from database import get_db_connection, run_query

DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()

def create_company(name: str) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        query = f"INSERT INTO companies (name) VALUES ({ph})"
        if DB_TYPE == "postgres":
            cur.execute(query + " RETURNING id", (name,))
            cid = cur.fetchone()[0]
        else:
            cur.execute(query, (name,))
            cid = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return cid
    except Exception as e:
        print(f"Erro create_company: {e}")
        if conn:
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
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        query = f"INSERT INTO partners (company_id, name, share_pct) VALUES ({ph}, {ph}, {ph})"
        if DB_TYPE == "postgres":
            cur.execute(query + " RETURNING id", (company_id, name, share_pct))
            pid = cur.fetchone()[0]
        else:
            cur.execute(query, (company_id, name, share_pct))
            pid = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return pid
    except Exception as e:
        print(f"Erro create_partner: {e}")
        if conn:
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
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        query = f"INSERT INTO products (company_id, sku, name, price) VALUES ({ph}, {ph}, {ph}, {ph})"
        if DB_TYPE == "postgres":
            cur.execute(query + " RETURNING id", (company_id, sku, name, price))
            pid = cur.fetchone()[0]
        else:
            cur.execute(query, (company_id, sku, name, price))
            pid = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return pid
    except Exception as e:
        print(f"Erro create_product: {e}")
        if conn:
            conn.close()
        return None

def get_products(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if company_id:
        res = run_query("SELECT * FROM products WHERE company_id = %s ORDER BY id DESC", (company_id,))
    else:
        res = run_query("SELECT * FROM products ORDER BY id DESC")
    return res or []

def add_stock_movement(product_id: int, quantity: int, movement_type: str, reference: Optional[str] = None, source: str = 'próprio', is_paid: bool = False, unit_cost: float = 0.0) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        query = f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference, source, is_paid, unit_cost) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})"
        if DB_TYPE == "postgres":
            cur.execute(query + " RETURNING id", (product_id, quantity, movement_type, reference, source, is_paid, unit_cost))
            mid = cur.fetchone()[0]
        else:
            cur.execute(query, (product_id, quantity, movement_type, reference, source, is_paid, unit_cost))
            mid = cur.lastrowid
        
        if movement_type == 'in' and is_paid and unit_cost > 0:
            total_cost = unit_cost * quantity
            dt = "CURRENT_DATE" if DB_TYPE == "postgres" else "date('now')"
            cur.execute(f"INSERT INTO transactions (type, amount, category, description, date, product_id) VALUES ('Despesa', {ph}, 'Estoque/Compra', {ph}, {dt}, {ph})", (total_cost, f"Compra: {reference}", product_id))
            
        conn.commit()
        cur.close()
        conn.close()
        return mid
    except Exception as e:
        print(f"Erro add_stock_movement: {e}")
        if conn:
            conn.close()
        return None

def get_stock_level(product_id: int) -> int:
    res = run_query("SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN quantity ELSE -quantity END),0) AS qty FROM stock_movements WHERE product_id = %s", (product_id,))
    if res and len(res) > 0:
        return int(res[0].get("qty", 0))
    return 0

def create_sale(product_id: int, quantity: int, unit_price: float, company_id: Optional[int] = None, partner_id: Optional[int] = None, description: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        avail = get_stock_level(product_id)
        if avail < quantity:
            raise Exception(f"Estoque insuficiente ({avail})")
        
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        cur.execute(f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference) VALUES ({ph}, {ph}, 'out', {ph})", (product_id, quantity, description))
        
        total = float(unit_price) * int(quantity)
        dt = "CURRENT_DATE" if DB_TYPE == "postgres" else "date('now')"
        q = f"INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) VALUES ('Receita', {ph}, 'Venda', {ph}, {dt}, {ph}, {ph}, {ph})"
        
        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", (total, description, product_id, partner_id, company_id))
            tid = cur.fetchone()[0]
        else:
            cur.execute(q, (total, description, product_id, partner_id, company_id))
            tid = cur.lastrowid
            
        conn.commit()
        cur.close()
        conn.close()
        return tid
    except Exception as e:
        print(f"Erro create_sale: {e}")
        if conn:
            conn.close()
        return None

def create_contribution(partner_id: int, amount: float, date: Optional[str] = None, note: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        dt_val = date if date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        ph_dt = ph if date else dt_val
        
        q = f"INSERT INTO contributions (partner_id, amount, date, note) VALUES ({ph}, {ph}, {ph_dt}, {ph})"
        params = (partner_id, amount, date, note) if date else (partner_id, amount, note)
            
        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            cid = cur.fetchone()[0]
        else:
            cur.execute(q, params)
            cid = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return cid
    except Exception as e:
        print(f"Erro contribution: {e}")
        if conn:
            conn.close()
        return None

def create_withdrawal(partner_id: int, amount: float, date: Optional[str] = None, reason: Optional[str] = None) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        dt_val = date if date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        ph_dt = ph if date else dt_val
        
        q = f"INSERT INTO withdrawals (partner_id, amount, date, reason) VALUES ({ph}, {ph}, {ph_dt}, {ph})"
        params = (partner_id, amount, date, reason) if date else (partner_id, amount, reason)
            
        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            wid = cur.fetchone()[0]
        else:
            cur.execute(q, params)
            wid = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()
        return wid
    except Exception as e:
        print(f"Erro withdrawal: {e}")
        if conn:
            conn.close()
        return None

def create_fixed_expense(company_id: int, name: str, amount: float, due_day: int):
    ph = "?" if DB_TYPE == "sqlite" else "%s"
    return run_query(f"INSERT INTO fixed_expenses (company_id, name, amount, due_day) VALUES ({ph}, {ph}, {ph}, {ph})", (company_id, name, amount, due_day))

def get_partner_reports(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
    SELECT 
        p.id, p.name, p.share_pct,
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Receita') AS total_revenue,
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Despesa') AS total_expenses,
        (SELECT COALESCE(SUM(c.amount), 0) FROM contributions c WHERE c.partner_id = p.id) AS total_contributed,
        (SELECT COALESCE(SUM(w.amount), 0) FROM withdrawals w WHERE w.partner_id = p.id) AS total_withdrawn
    FROM partners p
    """
    if company_id:
        query += f" WHERE p.company_id = {company_id}"
    res = run_query(query) or []
    
    # CMV global (custo dos produtos vendidos)
    cmv_res = run_query("""
        SELECT COALESCE(SUM(m.unit_cost * m.quantity), 0) as cmv
        FROM stock_movements m WHERE m.movement_type = 'out' AND m.unit_cost > 0
    """)
    cmv_total = float(cmv_res[0]['cmv']) if cmv_res else 0.0
    
    for r in res:
        # Lucro real = Receita - Despesas - CMV
        lucro_real = float(r['total_revenue']) - float(r['total_expenses']) - cmv_total
        # Cota do sócio no lucro operacional
        r['share_of_profit'] = lucro_real * (float(r['share_pct']) / 100.0)
        # Saldo = Cota no lucro + aportes feitos - retiradas já feitas
        r['current_balance'] = r['share_of_profit'] + float(r['total_contributed']) - float(r['total_withdrawn'])
    return res

def get_advanced_kpis(period: str = 'month'):
    if DB_TYPE == "postgres":
        if period == 'week': filter_sql = "date >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == 'month': filter_sql = "EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM CURRENT_DATE)"
        else: filter_sql = "EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:
        if period == 'week': filter_sql = "date >= date('now', '-7 days')"
        elif period == 'month': filter_sql = "strftime('%m', date) = strftime('%m', 'now')"
        else: filter_sql = "strftime('%Y', date) = strftime('%Y', 'now')"
    
    # Receita e despesas do período
    q_period = f"""SELECT 
        COALESCE(SUM(CASE WHEN type='Receita' THEN amount ELSE 0 END), 0) AS revenue,
        COALESCE(SUM(CASE WHEN type='Despesa' THEN amount ELSE 0 END), 0) AS expenses
    FROM transactions WHERE {filter_sql}"""
    
    # Saldo total do caixa: todas as receitas - todas as despesas + aportes de sócios - retiradas de sócios
    q_cash = """
    SELECT 
        (SELECT COALESCE(SUM(CASE WHEN type='Receita' THEN amount ELSE -amount END), 0) FROM transactions)
        + (SELECT COALESCE(SUM(amount), 0) FROM contributions)
        - (SELECT COALESCE(SUM(amount), 0) FROM withdrawals)
    AS total_cash
    """
    
    # CMV: custo dos produtos vendidos (saídas de estoque com custo registrado)
    q_cmv = f"""
    SELECT COALESCE(SUM(m.unit_cost * m.quantity), 0) as cmv
    FROM stock_movements m
    JOIN products p ON m.product_id = p.id
    WHERE m.movement_type = 'out' AND m.unit_cost > 0
    """
    
    res_period = run_query(q_period)
    res_cash = run_query(q_cash)
    res_cmv = run_query(q_cmv)
    
    if res_period and len(res_period) > 0:
        r = res_period[0]
        r['total_cash'] = res_cash[0]['total_cash'] if res_cash else 0
        cmv = float(res_cmv[0]['cmv']) if res_cmv else 0
        # Lucro real = Receita - Despesas - CMV (Custo dos produtos vendidos)
        r['net_profit'] = float(r['revenue']) - float(r['expenses']) - cmv
        r['cmv'] = cmv
        return [r]
    return None

def get_upcoming_alerts():
    day_fn = "EXTRACT(DAY FROM CURRENT_DATE)" if DB_TYPE == "postgres" else "strftime('%d', 'now')"
    query = f"SELECT * FROM fixed_expenses WHERE due_day >= {day_fn} AND due_day <= {day_fn} + 5"
    return run_query(query) or []

def get_inventory_report():
    query = """
    SELECT 
        p.id, p.name, p.price,
        COALESCE(SUM(CASE WHEN m.movement_type='in' THEN m.quantity ELSE -m.quantity END), 0) as stock_qty,
        COALESCE(MAX(CASE WHEN m.movement_type='in' THEN m.unit_cost ELSE NULL END), 0) as last_cost
    FROM products p
    LEFT JOIN stock_movements m ON p.id = m.product_id
    GROUP BY p.id, p.name, p.price
    """
    res = run_query(query) or []
    for r in res:
        qty = max(int(r['stock_qty']), 0)
        last_cost = float(r['last_cost'] or 0)
        price = float(r['price'] or 0)
        # Mostra valor total se há estoque, ou valor unitário se estoque zerado (pra nunca aparecer R$0,00)
        r['total_cost_value'] = last_cost * qty if qty > 0 else last_cost
        r['total_sale_value'] = price * qty if qty > 0 else price
        r['stock_qty'] = qty
    return res

def get_revenue_details():
    res = run_query("SELECT CASE WHEN product_id IS NOT NULL THEN 'Venda' ELSE 'Servico' END as channel, SUM(amount) as total FROM transactions WHERE type = 'Receita' GROUP BY channel") or []
    return res

def get_expense_types(company_id=None):
    q = "SELECT * FROM expense_types"
    if company_id:
        q += f" WHERE company_id = {company_id}"
    return run_query(q) or []

def get_income_types(company_id=None):
    q = "SELECT * FROM income_types"
    if company_id:
        q += f" WHERE company_id = {company_id}"
    return run_query(q) or []

def get_categories(tipo: str) -> List[str]:
    """Retorna lista de nomes de categoria para 'Receita' ou 'Despesa'."""
    table = "income_types" if tipo == "Receita" else "expense_types"
    res = run_query(f"SELECT name FROM {table} ORDER BY name") or []
    return [r['name'] for r in res]

def create_category(tipo: str, name: str, company_id: int = 1) -> bool:
    """Cria uma nova categoria de Receita ou Despesa se não existir."""
    table = "income_types" if tipo == "Receita" else "expense_types"
    ph = "?" if DB_TYPE == "sqlite" else "%s"
    existing = run_query(f"SELECT id FROM {table} WHERE name = {ph}", (name,))
    if existing:
        return True  # já existe
    res = run_query(f"INSERT INTO {table} (company_id, name) VALUES ({ph}, {ph})", (company_id, name))
    return res is True

def delete_transaction(transaction_id: int) -> bool:
    """Deleta um lançamento financeiro pelo ID."""
    res = run_query("DELETE FROM transactions WHERE id = %s", (transaction_id,))
    return res is True

def get_all_transactions(limit: int = 300) -> List[Dict[str, Any]]:
    """Busca o histórico unificado (financeiro e estoque), garantindo visibilidade total."""
    # SQLite usa date('now'), Postgres usa CURRENT_DATE. Usamos coalesce e formatos compatíveis.
    # Usamos LEFT JOIN para garantir que movimentos de estoque sem produto (ou com produto deletado) apareçam.
    query = f"""
    SELECT id, CAST(date AS TEXT) as date, type, amount, category, description FROM transactions
    UNION ALL
    SELECT m.id, CAST(date(m.created_at) AS TEXT) as date, 'Estoque' as type, 
           (COALESCE(m.unit_cost, 0) * m.quantity) as amount, m.movement_type as category, 
           COALESCE(p.name, 'Produto Removido') || ' (' || COALESCE(m.reference, '') || ')' as description 
    FROM stock_movements m
    LEFT JOIN products p ON m.product_id = p.id
    ORDER BY date DESC, id DESC LIMIT {limit}
    """
    return run_query(query) or []

def get_detailed_stock_report() -> List[Dict[str, Any]]:
    """Relatório para a aba de gestão: o que temos, o que saiu e valores."""
    query = """
    SELECT 
        p.id, p.sku, p.name, p.price,
        COALESCE(SUM(CASE WHEN m.movement_type='in' THEN m.quantity ELSE 0 END), 0) as total_in,
        COALESCE(SUM(CASE WHEN m.movement_type='out' THEN m.quantity ELSE 0 END), 0) as total_out,
        COALESCE(SUM(CASE WHEN m.movement_type='in' THEN m.quantity ELSE -m.quantity END), 0) as current_stock,
        COALESCE(MAX(m.unit_cost), 0) as last_cost
    FROM products p
    LEFT JOIN stock_movements m ON p.id = m.product_id
    GROUP BY p.id, p.sku, p.name, p.price
    ORDER BY current_stock DESC
    """
    res = run_query(query) or []
    for r in res:
        r['stock_value_cost'] = float(r['last_cost']) * int(r['current_stock'])
        r['stock_value_sale'] = float(r['price']) * int(r['current_stock'])
    return res
