from typing import Optional, List, Dict, Any
import os
from database import get_db_connection, run_query

DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()
NON_OPERATIONAL_CATEGORIES = ("Emprestimo Socios", "Amortizacao Emprestimo", "Estoque/Compra", "Estoque/Custo Adicional")
INFRA_INVESTMENT_CATEGORIES = ("Infraestrutura", "Software/Infra")


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(_sql_quote(v) for v in values)


NON_OPERATIONAL_SQL = _sql_in_list(NON_OPERATIONAL_CATEGORIES)
INFRA_INVESTMENT_SQL = _sql_in_list(INFRA_INVESTMENT_CATEGORIES)
PROFIT_EXPENSE_EXCLUSIONS_SQL = _sql_in_list(NON_OPERATIONAL_CATEGORIES + INFRA_INVESTMENT_CATEGORIES)


def _safe_limit(limit: int, default: int = 300, maximum: int = 5000) -> int:
    try:
        value = int(limit)
        if value < 1:
            return default
        return min(value, maximum)
    except Exception:
        return default


def _table_exists(table_name: str) -> bool:
    try:
        if DB_TYPE == "sqlite":
            res = run_query("SELECT name FROM sqlite_master WHERE type='table' AND name = %s", (table_name,))
        else:
            res = run_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name = %s",
                (table_name,)
            )
        return bool(res)
    except Exception:
        return False


def _get_latest_in_unit_cost(product_id: int) -> float:
    rows = run_query(
        "SELECT unit_cost FROM stock_movements WHERE product_id = %s AND movement_type='in' AND unit_cost > 0 ORDER BY id DESC LIMIT 1",
        (product_id,)
    ) or []
    if not rows:
        return 0.0
    return float(rows[0].get("unit_cost") or 0.0)

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
        qty = int(quantity)
        if qty <= 0:
            raise Exception("Quantidade deve ser maior que zero.")
        if movement_type not in ("in", "out"):
            raise Exception("Tipo de movimento inválido.")
        if movement_type == "out":
            avail = get_stock_level(product_id)
            if avail < qty:
                raise Exception(f"Estoque insuficiente ({avail})")
            if float(unit_cost or 0) <= 0:
                unit_cost = _get_latest_in_unit_cost(product_id)

        ph = "?" if DB_TYPE == "sqlite" else "%s"
        query = f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference, source, is_paid, unit_cost) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})"
        if DB_TYPE == "postgres":
            cur.execute(query + " RETURNING id", (product_id, qty, movement_type, reference, source, is_paid, unit_cost))
            mid = cur.fetchone()[0]
        else:
            cur.execute(query, (product_id, qty, movement_type, reference, source, is_paid, unit_cost))
            mid = cur.lastrowid
        
        if movement_type == 'in' and is_paid and unit_cost > 0:
            total_cost = unit_cost * qty
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


def create_product_cost_adjustment(
    product_id: int,
    amount: float,
    date: Optional[str] = None,
    note: Optional[str] = None,
    is_paid: bool = True
) -> Optional[int]:
    """
    Registra custo adicional no estoque atual do produto.
    O valor é distribuído por unidade para compor o CMV nas próximas saídas.
    """
    if not _table_exists("product_cost_adjustments"):
        return None

    total = float(amount or 0)
    if total <= 0:
        return None

    base_qty = get_stock_level(product_id)
    if base_qty <= 0:
        return None

    unit_increment = total / base_qty
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        dt_val = date if date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if date else dt_val

        q = (
            f"INSERT INTO product_cost_adjustments "
            f"(product_id, total_amount, base_qty, remaining_qty, unit_increment, date, note) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {dt_sql}, {ph})"
        )
        params = (product_id, total, base_qty, base_qty, unit_increment, date, note) if date else (product_id, total, base_qty, base_qty, unit_increment, note)

        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            adj_id = cur.fetchone()[0]
        else:
            cur.execute(q, params)
            adj_id = cur.lastrowid

        if is_paid:
            tx_q = f"INSERT INTO transactions (type, amount, category, description, date, product_id) VALUES ('Despesa', {ph}, 'Estoque/Custo Adicional', {ph}, {dt_sql}, {ph})"
            tx_desc = f"[ADJCOST:{adj_id}] {note or 'Custo adicional de produto'}"
            tx_params = (total, tx_desc, date, product_id) if date else (total, tx_desc, product_id)
            cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return adj_id
    except Exception as e:
        print(f"Erro create_product_cost_adjustment: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None

def create_sale(
    product_id: int,
    quantity: int,
    unit_price: float,
    company_id: Optional[int] = None,
    partner_id: Optional[int] = None,
    description: Optional[str] = None,
    sale_date: Optional[str] = None
) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        qty_sold = int(quantity)
        avail = get_stock_level(product_id)
        if avail < qty_sold:
            raise Exception(f"Estoque insuficiente ({avail})")
        
        out_unit_cost = _get_latest_in_unit_cost(product_id)
        extra_cost_total = 0.0

        # Consome custos adicionais pendentes para aumentar CMV das saídas.
        if _table_exists("product_cost_adjustments"):
            ph = "?" if DB_TYPE == "sqlite" else "%s"
            cur.execute(
                f"SELECT id, unit_increment, remaining_qty FROM product_cost_adjustments WHERE product_id = {ph} AND remaining_qty > 0 ORDER BY id ASC",
                (product_id,)
            )
            adjustments = cur.fetchall() or []
            qty_left = qty_sold
            for adj in adjustments:
                adj_id = adj[0]
                unit_inc = float(adj[1] or 0)
                rem_qty = int(adj[2] or 0)
                if qty_left <= 0:
                    break
                if rem_qty <= 0 or unit_inc <= 0:
                    continue
                alloc_qty = min(qty_left, rem_qty)
                extra_cost_total += alloc_qty * unit_inc
                new_rem = rem_qty - alloc_qty
                cur.execute(
                    f"UPDATE product_cost_adjustments SET remaining_qty = {ph} WHERE id = {ph}",
                    (new_rem, adj_id)
                )
                qty_left -= alloc_qty

        blended_unit_cost = out_unit_cost + (extra_cost_total / qty_sold if qty_sold > 0 else 0.0)
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        cur.execute(
            f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference, unit_cost) VALUES ({ph}, {ph}, 'out', {ph}, {ph})",
            (product_id, qty_sold, description, blended_unit_cost)
        )
        
        total = float(unit_price) * qty_sold
        dt_val = sale_date if sale_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if sale_date else dt_val
        q = f"INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) VALUES ('Receita', {ph}, 'Venda', {ph}, {dt_sql}, {ph}, {ph}, {ph})"
        params = (total, description, sale_date, product_id, partner_id, company_id) if sale_date else (total, description, product_id, partner_id, company_id)
        
        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            tid = cur.fetchone()[0]
        else:
            cur.execute(q, params)
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


def create_partner_loan(
    partner_id: int,
    direction: str,
    amount: float,
    loan_date: Optional[str] = None,
    due_date: Optional[str] = None,
    interest_rate: float = 0.0,
    note: Optional[str] = None
) -> Optional[int]:
    """
    Registra empréstimo entre sócio e empresa.
    direction:
      - partner_to_company: sócio empresta para empresa (entrada de caixa)
      - company_to_partner: empresa empresta para sócio (saída de caixa)
    """
    if direction not in ("partner_to_company", "company_to_partner"):
        return None
    if not _table_exists("partner_loans") or not _table_exists("partner_loan_payments"):
        return None

    amount = float(amount or 0)
    if amount <= 0:
        return None

    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        dt_val = loan_date if loan_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if loan_date else dt_val
        due_sql = ph

        q = (
            f"INSERT INTO partner_loans (partner_id, direction, principal_amount, outstanding_amount, interest_rate, loan_date, due_date, note, status) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {dt_sql}, {due_sql}, {ph}, 'open')"
        )
        params = (
            (partner_id, direction, amount, amount, float(interest_rate or 0), loan_date, due_date, note)
            if loan_date
            else (partner_id, direction, amount, amount, float(interest_rate or 0), due_date, note)
        )

        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            loan_id = cur.fetchone()[0]
        else:
            cur.execute(q, params)
            loan_id = cur.lastrowid

        t_type = "Receita" if direction == "partner_to_company" else "Despesa"
        direction_label = "Sócio->Empresa" if direction == "partner_to_company" else "Empresa->Sócio"
        dt_tx = dt_sql
        tx_q = (
            f"INSERT INTO transactions (type, amount, category, description, date, partner_id) "
            f"VALUES ({ph}, {ph}, 'Empréstimo Sócios', {ph}, {dt_tx}, {ph})"
        )
        tx_desc = f"[LOAN:{loan_id}] Empréstimo {direction_label}. {note or ''}".strip()
        tx_params = (t_type, amount, tx_desc, loan_date, partner_id) if loan_date else (t_type, amount, tx_desc, partner_id)
        cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return loan_id
    except Exception as e:
        print(f"Erro create_partner_loan: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None


def add_partner_loan_payment(
    loan_id: int,
    amount: float,
    payment_date: Optional[str] = None,
    note: Optional[str] = None
) -> Optional[int]:
    if not _table_exists("partner_loans") or not _table_exists("partner_loan_payments"):
        return None
    amount = float(amount or 0)
    if amount <= 0:
        return None

    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        loan_rows = run_query(
            "SELECT id, partner_id, direction, outstanding_amount, status FROM partner_loans WHERE id = %s",
            (loan_id,)
        ) or []
        if not loan_rows:
            return None
        loan = loan_rows[0]
        if loan.get("status") != "open":
            return None

        outstanding = float(loan.get("outstanding_amount") or 0)
        if amount > outstanding:
            return None

        dt_val = payment_date if payment_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if payment_date else dt_val

        q = f"INSERT INTO partner_loan_payments (loan_id, amount, payment_date, note) VALUES ({ph}, {ph}, {dt_sql}, {ph})"
        params = (loan_id, amount, payment_date, note) if payment_date else (loan_id, amount, note)
        if DB_TYPE == "postgres":
            cur.execute(q + " RETURNING id", params)
            payment_id = cur.fetchone()[0]
        else:
            cur.execute(q, params)
            payment_id = cur.lastrowid

        new_outstanding = max(outstanding - amount, 0.0)
        new_status = "paid" if new_outstanding <= 0 else "open"
        cur.execute(
            f"UPDATE partner_loans SET outstanding_amount = {ph}, status = {ph} WHERE id = {ph}",
            (new_outstanding, new_status, loan_id)
        )

        # Fluxo de caixa da amortização:
        # partner_to_company -> empresa paga (Despesa)
        # company_to_partner -> empresa recebe (Receita)
        t_type = "Despesa" if loan.get("direction") == "partner_to_company" else "Receita"
        tx_desc = f"[LOANPAY:{payment_id}|LOAN:{loan_id}] Amortização empréstimo. {note or ''}".strip()
        tx_q = (
            f"INSERT INTO transactions (type, amount, category, description, date, partner_id) "
            f"VALUES ({ph}, {ph}, 'Amortização Empréstimo', {ph}, {dt_sql}, {ph})"
        )
        tx_params = (t_type, amount, tx_desc, payment_date, loan.get("partner_id")) if payment_date else (t_type, amount, tx_desc, loan.get("partner_id"))
        cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return payment_id
    except Exception as e:
        print(f"Erro add_partner_loan_payment: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None


def get_partner_loans(partner_id: Optional[int] = None, status: Optional[str] = None):
    if not _table_exists("partner_loans"):
        return []
    query = """
    SELECT
        l.id,
        l.partner_id,
        p.name AS partner_name,
        l.direction,
        l.principal_amount,
        l.outstanding_amount,
        l.interest_rate,
        l.loan_date,
        l.due_date,
        l.note,
        l.status,
        l.created_at
    FROM partner_loans l
    LEFT JOIN partners p ON p.id = l.partner_id
    WHERE 1=1
    """
    params = []
    if partner_id:
        query += " AND l.partner_id = %s"
        params.append(partner_id)
    if status:
        query += " AND l.status = %s"
        params.append(status)
    query += " ORDER BY l.loan_date DESC, l.id DESC"
    return run_query(query, tuple(params) if params else None) or []


def get_partner_loans_summary():
    if not _table_exists("partner_loans"):
        return []
    query = """
    SELECT
        p.id AS partner_id,
        p.name AS partner_name,
        COALESCE(SUM(CASE WHEN l.direction='partner_to_company' AND l.status='open' THEN l.outstanding_amount ELSE 0 END), 0) AS company_owes_partner,
        COALESCE(SUM(CASE WHEN l.direction='company_to_partner' AND l.status='open' THEN l.outstanding_amount ELSE 0 END), 0) AS partner_owes_company
    FROM partners p
    LEFT JOIN partner_loans l ON l.partner_id = p.id
    GROUP BY p.id, p.name
    ORDER BY p.name
    """
    return run_query(query) or []

def create_fixed_expense(company_id: int, name: str, amount: float, due_day: int):
    ph = "?" if DB_TYPE == "sqlite" else "%s"
    return run_query(f"INSERT INTO fixed_expenses (company_id, name, amount, due_day) VALUES ({ph}, {ph}, {ph}, {ph})", (company_id, name, amount, due_day))

def get_partner_reports(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
    SELECT 
        p.id, p.name, p.share_pct,
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Receita' AND COALESCE(category,'') NOT IN (""" + NON_OPERATIONAL_SQL + """)) AS total_revenue,
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Despesa' AND COALESCE(category,'') NOT IN (""" + PROFIT_EXPENSE_EXCLUSIONS_SQL + """)) AS total_expenses,
        (SELECT COALESCE(SUM(c.amount), 0) FROM contributions c WHERE c.partner_id = p.id) AS total_contributed,
        (SELECT COALESCE(SUM(w.amount), 0) FROM withdrawals w WHERE w.partner_id = p.id) AS total_withdrawn
    FROM partners p
    """
    if company_id:
        query += " WHERE p.company_id = %s"
        res = run_query(query, (company_id,)) or []
    else:
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
        if period == 'week':
            filter_sql = "date >= CURRENT_DATE - INTERVAL '7 days'"
            movement_filter_sql = "DATE(m.created_at) >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == 'month':
            filter_sql = "DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE)"
            movement_filter_sql = "DATE_TRUNC('month', m.created_at) = DATE_TRUNC('month', CURRENT_DATE)"
        else:
            filter_sql = "EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)"
            movement_filter_sql = "EXTRACT(YEAR FROM m.created_at) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:
        if period == 'week':
            filter_sql = "date >= date('now', '-7 days')"
            movement_filter_sql = "date(m.created_at) >= date('now', '-7 days')"
        elif period == 'month':
            filter_sql = "strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            movement_filter_sql = "strftime('%Y-%m', m.created_at) = strftime('%Y-%m', 'now')"
        else:
            filter_sql = "strftime('%Y', date) = strftime('%Y', 'now')"
            movement_filter_sql = "strftime('%Y', m.created_at) = strftime('%Y', 'now')"
    
    # Receita e despesas do período
    q_period = f"""SELECT 
        COALESCE(SUM(CASE WHEN type='Receita' AND COALESCE(category,'') NOT IN ({NON_OPERATIONAL_SQL}) THEN amount ELSE 0 END), 0) AS revenue,
        COALESCE(SUM(CASE WHEN type='Despesa' AND COALESCE(category,'') NOT IN ({PROFIT_EXPENSE_EXCLUSIONS_SQL}) THEN amount ELSE 0 END), 0) AS expenses,
        COALESCE(SUM(CASE WHEN type='Despesa' AND COALESCE(category,'') IN ({INFRA_INVESTMENT_SQL}) THEN amount ELSE 0 END), 0) AS infra_investment
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
    WHERE m.movement_type = 'out' AND m.unit_cost > 0 AND {movement_filter_sql}
    """
    
    res_period = run_query(q_period)
    res_cash = run_query(q_cash)
    res_cmv = run_query(q_cmv)
    
    if res_period and len(res_period) > 0:
        r = res_period[0]
        r['total_cash'] = res_cash[0]['total_cash'] if res_cash else 0
        cmv = float(res_cmv[0]['cmv']) if res_cmv else 0
        # Lucro operacional exclui investimentos em infraestrutura.
        r['net_profit'] = float(r['revenue']) - float(r['expenses']) - cmv
        r['accounting_profit'] = r['net_profit'] - float(r.get('infra_investment') or 0)
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
        # Para indicadores de estoque, só conta o que está disponível hoje.
        r['total_cost_value'] = last_cost * qty
        r['total_sale_value'] = price * qty
        r['stock_qty'] = qty
    return res

def get_revenue_details():
    res = run_query(
        "SELECT CASE WHEN product_id IS NOT NULL THEN 'Venda' ELSE 'Servico' END as channel, SUM(amount) as total "
        "FROM transactions "
        f"WHERE type = 'Receita' AND COALESCE(category,'') NOT IN ({NON_OPERATIONAL_SQL}) "
        "GROUP BY channel"
    ) or []
    return res


def get_infra_inventory():
    query = f"""
    SELECT
        COALESCE(NULLIF(TRIM(description), ''), category) AS item_name,
        category,
        COUNT(*) AS entries,
        MAX(date) AS last_date,
        COALESCE(SUM(amount), 0) AS total_invested
    FROM transactions
    WHERE type = 'Despesa'
      AND COALESCE(category, '') IN ({INFRA_INVESTMENT_SQL})
    GROUP BY COALESCE(NULLIF(TRIM(description), ''), category), category
    ORDER BY last_date DESC, total_invested DESC
    """
    return run_query(query) or []

def get_expense_types(company_id=None):
    if company_id:
        return run_query("SELECT * FROM expense_types WHERE company_id = %s", (company_id,)) or []
    return run_query("SELECT * FROM expense_types") or []

def get_income_types(company_id=None):
    if company_id:
        return run_query("SELECT * FROM income_types WHERE company_id = %s", (company_id,)) or []
    return run_query("SELECT * FROM income_types") or []

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
    """Compatibilidade: remove um item financeiro e reverte estoque em caso de venda."""
    return delete_history_item("transaction", transaction_id)


def delete_history_item(source: str, record_id: int) -> bool:
    """
    Remove item do histórico.
    - source='transaction': remove transação; se for venda, remove também 1 saída de estoque correlata.
    - source='stock': remove movimentação de estoque diretamente.
    """
    if source == "contribution":
        res = run_query("DELETE FROM contributions WHERE id = %s", (record_id,))
        return res is True

    if source == "withdrawal":
        res = run_query("DELETE FROM withdrawals WHERE id = %s", (record_id,))
        return res is True

    if source == "cost_adjustment":
        if not _table_exists("product_cost_adjustments"):
            return False
        adj_rows = run_query(
            "SELECT id, base_qty, remaining_qty FROM product_cost_adjustments WHERE id = %s",
            (record_id,)
        ) or []
        if not adj_rows:
            return False
        adj = adj_rows[0]
        # Só permite cancelar se nenhum custo adicional já foi consumido em saídas.
        if int(adj.get("remaining_qty") or 0) < int(adj.get("base_qty") or 0):
            return False
        run_query(
            "DELETE FROM transactions WHERE category = 'Estoque/Custo Adicional' AND description LIKE %s",
            (f"[ADJCOST:{record_id}]%",)
        )
        res = run_query("DELETE FROM product_cost_adjustments WHERE id = %s", (record_id,))
        return res is True

    if source == "loan":
        if not _table_exists("partner_loans") or not _table_exists("partner_loan_payments"):
            return False
        # Não permite cancelar empréstimo com amortizações já registradas.
        has_payments = run_query("SELECT id FROM partner_loan_payments WHERE loan_id = %s LIMIT 1", (record_id,)) or []
        if has_payments:
            return False

        # Remove transação financeira vinculada ao registro de empréstimo.
        run_query(
            "DELETE FROM transactions WHERE category = 'Empréstimo Sócios' AND description LIKE %s",
            (f"[LOAN:{record_id}]%",)
        )
        res = run_query("DELETE FROM partner_loans WHERE id = %s", (record_id,))
        return res is True

    if source == "loan_payment":
        if not _table_exists("partner_loans") or not _table_exists("partner_loan_payments"):
            return False
        pay_rows = run_query(
            "SELECT id, loan_id, amount FROM partner_loan_payments WHERE id = %s",
            (record_id,)
        ) or []
        if not pay_rows:
            return False
        pay = pay_rows[0]

        # Reverte saldo do empréstimo.
        run_query(
            "UPDATE partner_loans SET outstanding_amount = outstanding_amount + %s, status = 'open' WHERE id = %s",
            (pay["amount"], pay["loan_id"])
        )
        # Remove transação financeira vinculada à amortização.
        run_query(
            "DELETE FROM transactions WHERE category = 'Amortização Empréstimo' AND description LIKE %s",
            (f"[LOANPAY:{record_id}|LOAN:{pay['loan_id']}]%",)
        )
        res = run_query("DELETE FROM partner_loan_payments WHERE id = %s", (record_id,))
        return res is True

    if source == "stock":
        mv_rows = run_query(
            "SELECT id, product_id, movement_type, reference FROM stock_movements WHERE id = %s",
            (record_id,)
        ) or []
        if not mv_rows:
            return False
        mv = mv_rows[0]
        # Se for saída de estoque ligada à venda, remove também a transação de receita correspondente.
        if mv.get("movement_type") == "out" and mv.get("product_id"):
            if mv.get("reference"):
                tx = run_query(
                    "SELECT id FROM transactions WHERE type='Receita' AND category='Venda' AND product_id = %s AND description = %s ORDER BY id DESC LIMIT 1",
                    (mv["product_id"], mv["reference"])
                ) or []
            else:
                tx = run_query(
                    "SELECT id FROM transactions WHERE type='Receita' AND category='Venda' AND product_id = %s ORDER BY id DESC LIMIT 1",
                    (mv["product_id"],)
                ) or []
            if tx:
                run_query("DELETE FROM transactions WHERE id = %s", (tx[0]["id"],))
        res = run_query("DELETE FROM stock_movements WHERE id = %s", (record_id,))
        return res is True

    tx_rows = run_query(
        "SELECT id, type, category, product_id, description FROM transactions WHERE id = %s",
        (record_id,)
    ) or []
    if not tx_rows:
        return False

    tx = tx_rows[0]
    # Venda: ao cancelar a transação, desfaz também a saída de estoque correspondente.
    if tx.get("type") == "Receita" and tx.get("category") == "Venda" and tx.get("product_id"):
        product_id = tx.get("product_id")
        description = tx.get("description")
        if description:
            mv = run_query(
                "SELECT id FROM stock_movements WHERE product_id = %s AND movement_type='out' AND reference = %s ORDER BY id DESC LIMIT 1",
                (product_id, description)
            ) or []
        else:
            mv = run_query(
                "SELECT id FROM stock_movements WHERE product_id = %s AND movement_type='out' ORDER BY id DESC LIMIT 1",
                (product_id,)
            ) or []
        if mv:
            run_query("DELETE FROM stock_movements WHERE id = %s", (mv[0]["id"],))

    res = run_query("DELETE FROM transactions WHERE id = %s", (record_id,))
    return res is True

def get_all_transactions(limit: int = 300) -> List[Dict[str, Any]]:
    """Busca o histórico unificado (financeiro e estoque), garantindo visibilidade total."""
    safe_limit = _safe_limit(limit)
    parts = [
        """
        SELECT
            id,
            CAST(date AS TEXT) as date,
            type,
            amount,
            category,
            description,
            'transaction' as source,
            id as source_id
        FROM transactions
        WHERE COALESCE(category, '') NOT IN ('Empréstimo Sócios', 'Amortização Empréstimo', 'Estoque/Custo Adicional')
        """,
        """
        SELECT
            c.id,
            CAST(c.date AS TEXT) as date,
            'Aporte Sócio' as type,
            c.amount as amount,
            'Aporte' as category,
            COALESCE(p.name, 'Sócio Removido') || ' (' || COALESCE(c.note, '') || ')' as description,
            'contribution' as source,
            c.id as source_id
        FROM contributions c
        LEFT JOIN partners p ON c.partner_id = p.id
        """,
        """
        SELECT
            w.id,
            CAST(w.date AS TEXT) as date,
            'Retirada Sócio' as type,
            w.amount as amount,
            'Retirada' as category,
            COALESCE(p.name, 'Sócio Removido') || ' (' || COALESCE(w.reason, '') || ')' as description,
            'withdrawal' as source,
            w.id as source_id
        FROM withdrawals w
        LEFT JOIN partners p ON w.partner_id = p.id
        """,
        """
        SELECT
            m.id,
            CAST(date(m.created_at) AS TEXT) as date,
            'Estoque' as type,
            (COALESCE(m.unit_cost, 0) * m.quantity) as amount,
            m.movement_type as category,
            COALESCE(p.name, 'Produto Removido') || ' (' || COALESCE(m.reference, '') || ')' as description,
            'stock' as source,
            m.id as source_id
        FROM stock_movements m
        LEFT JOIN products p ON m.product_id = p.id
        """
    ]

    if _table_exists("partner_loans"):
        parts.append(
            """
            SELECT
                l.id,
                CAST(l.loan_date AS TEXT) as date,
                CASE WHEN l.direction='partner_to_company' THEN 'Empréstimo Sócio->Empresa' ELSE 'Empréstimo Empresa->Sócio' END as type,
                l.principal_amount as amount,
                'Empréstimo Sócios' as category,
                COALESCE(p.name, 'Sócio Removido') || ' (' || COALESCE(l.note, '') || ')' as description,
                'loan' as source,
                l.id as source_id
            FROM partner_loans l
            LEFT JOIN partners p ON l.partner_id = p.id
            """
        )

    if _table_exists("product_cost_adjustments"):
        parts.append(
            """
            SELECT
                a.id,
                CAST(a.date AS TEXT) as date,
                'Custo Adicional Produto' as type,
                a.total_amount as amount,
                'Estoque/Custo Adicional' as category,
                COALESCE(p.name, 'Produto Removido') || ' (' || COALESCE(a.note, '') || ')' as description,
                'cost_adjustment' as source,
                a.id as source_id
            FROM product_cost_adjustments a
            LEFT JOIN products p ON p.id = a.product_id
            """
        )

    if _table_exists("partner_loan_payments") and _table_exists("partner_loans"):
        parts.append(
            """
            SELECT
                pay.id,
                CAST(pay.payment_date AS TEXT) as date,
                'Amortização Empréstimo' as type,
                pay.amount as amount,
                'Amortização Empréstimo' as category,
                COALESCE(p.name, 'Sócio Removido') || ' (' || COALESCE(pay.note, '') || ')' as description,
                'loan_payment' as source,
                pay.id as source_id
            FROM partner_loan_payments pay
            LEFT JOIN partner_loans l ON l.id = pay.loan_id
            LEFT JOIN partners p ON l.partner_id = p.id
            """
        )

    query = " UNION ALL ".join(parts) + f" ORDER BY date DESC, id DESC LIMIT {safe_limit}"
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

