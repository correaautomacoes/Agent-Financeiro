from typing import Optional, List, Dict, Any
import os
from database import get_db_connection, run_query

DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()
NON_OPERATIONAL_CATEGORIES = (
    "Emprestimo Socios",
    "Empr\u00e9stimo S\u00f3cios",
    "Amortizacao Emprestimo",
    "Amortiza\u00e7\u00e3o Empr\u00e9stimo",
    "Estoque/Compra",
    "Estoque/Custo Adicional",
    "Venda a Prazo",
)
INFRA_INVESTMENT_CATEGORIES = ("Infraestrutura", "Software/Infra")


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(_sql_quote(v) for v in values)


NON_OPERATIONAL_SQL = _sql_in_list(NON_OPERATIONAL_CATEGORIES)
INFRA_INVESTMENT_SQL = _sql_in_list(INFRA_INVESTMENT_CATEGORIES)
PROFIT_EXPENSE_EXCLUSIONS_SQL = _sql_in_list(NON_OPERATIONAL_CATEGORIES + INFRA_INVESTMENT_CATEGORIES)
LOAN_TAG_EXCLUSION_SQL = "COALESCE(description,'') NOT LIKE '[LOAN:%' AND COALESCE(description,'') NOT LIKE '[LOANPAY:%'"
# Blindagem extra para dados legados/manuais sem tags padronizadas.
LOAN_TEXT_EXCLUSION_SQL = (
    "LOWER(COALESCE(category,'')) NOT LIKE '%emprest%' "
    "AND LOWER(COALESCE(category,'')) NOT LIKE '%emprést%' "
    "AND LOWER(COALESCE(category,'')) NOT LIKE '%amortiz%' "
    "AND LOWER(COALESCE(description,'')) NOT LIKE '%emprest%' "
    "AND LOWER(COALESCE(description,'')) NOT LIKE '%emprést%' "
    "AND LOWER(COALESCE(description,'')) NOT LIKE '%amortiz%'"
)
NON_OPERATIONAL_EXCLUSION_SQL = f"{LOAN_TAG_EXCLUSION_SQL} AND {LOAN_TEXT_EXCLUSION_SQL}"


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


def _get_pending_cost_adjustments(product_id: int):
    if not _table_exists("product_cost_adjustments"):
        return []
    rows = run_query(
        "SELECT id, unit_increment, remaining_qty FROM product_cost_adjustments WHERE product_id = %s AND remaining_qty > 0 ORDER BY id ASC",
        (product_id,)
    ) or []
    return rows


def estimate_sale_cost(product_id: int, quantity: int = 1) -> Dict[str, float]:
    qty = max(int(quantity or 0), 0)
    if qty <= 0:
        return {
            "base_unit_cost": 0.0,
            "extra_cost_total": 0.0,
            "estimated_total_cost": 0.0,
            "estimated_unit_cost": 0.0,
            "pending_adjustment_total": 0.0,
        }

    base_unit_cost = _get_latest_in_unit_cost(product_id)
    extra_cost_total = 0.0

    for adj in _get_pending_cost_adjustments(product_id):
        unit_inc = float(adj.get("unit_increment") or 0.0)
        rem_qty = int(adj.get("remaining_qty") or 0)
        if unit_inc <= 0 or rem_qty <= 0:
            continue
        alloc_qty = min(qty, rem_qty)
        extra_cost_total += alloc_qty * unit_inc

    estimated_total_cost = (base_unit_cost * qty) + extra_cost_total
    estimated_unit_cost = estimated_total_cost / qty if qty > 0 else 0.0
    pending_adjustment_total = sum(
        float(adj.get("unit_increment") or 0.0) * int(adj.get("remaining_qty") or 0)
        for adj in _get_pending_cost_adjustments(product_id)
    )

    return {
        "base_unit_cost": base_unit_cost,
        "extra_cost_total": extra_cost_total,
        "estimated_total_cost": estimated_total_cost,
        "estimated_unit_cost": estimated_unit_cost,
        "pending_adjustment_total": pending_adjustment_total,
    }

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

def add_stock_movement(product_id: int, quantity: int, movement_type: str, reference: Optional[str] = None, source: str = 'próprio', is_paid: bool = False, unit_cost: float = 0.0, movement_date: Optional[str] = None, record_expense: bool = True) -> Optional[int]:
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

        if movement_type == 'in' and is_paid and unit_cost > 0 and record_expense:
            total_cost = unit_cost * qty

            if movement_date:
                if DB_TYPE == 'postgres':
                    date_expr = '%s'
                    tx_date_val = movement_date
                else:
                    date_expr = '?'
                    tx_date_val = movement_date
            else:
                date_expr = "CURRENT_DATE" if DB_TYPE == "postgres" else "date('now')"
                tx_date_val = None

            if date_expr in ('CURRENT_DATE', "date('now')"):
                cur.execute(
                    f"INSERT INTO transactions (type, amount, category, description, date, product_id) VALUES ('Despesa', {ph}, 'Estoque/Compra', {ph}, {date_expr}, {ph})",
                    (total_cost, f"Compra: {reference}", product_id)
                )
            else:
                cur.execute(
                    f"INSERT INTO transactions (type, amount, category, description, date, product_id) VALUES ('Despesa', {ph}, 'Estoque/Compra', {ph}, {date_expr}, {ph})",
                    (total_cost, f"Compra: {reference}", tx_date_val, product_id)
                )

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

def get_receivables_summary() -> Dict[str, float]:
    if not _table_exists("receivables"):
        return {"pending_total": 0.0, "received_total": 0.0, "overdue_total": 0.0}

    rows = run_query(
        """
        SELECT
            COALESCE(SUM(CASE WHEN status = 'pending' THEN amount - COALESCE(paid_amount, 0) ELSE 0 END), 0) AS pending_total,
            COALESCE(SUM(CASE WHEN status = 'paid' THEN COALESCE(paid_amount, amount) ELSE 0 END), 0) AS received_total,
            COALESCE(SUM(CASE
                WHEN status = 'pending' AND due_date < (CURRENT_DATE) THEN amount - COALESCE(paid_amount, 0)
                ELSE 0
            END), 0) AS overdue_total
        FROM receivables
        """
    ) or []
    if not rows:
        return {"pending_total": 0.0, "received_total": 0.0, "overdue_total": 0.0}
    return rows[0]


def receive_installment(receivable_id: int, amount: float, payment_date: Optional[str] = None, note: Optional[str] = None) -> bool:
    if not _table_exists("receivables"):
        return False

    amount = float(amount or 0)
    if amount <= 0:
        return False

    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"

        rows = run_query("SELECT * FROM receivables WHERE id = %s", (receivable_id,)) or []
        if not rows:
            return False
        row = rows[0]
        if row.get("status") == "paid":
            return False

        total = float(row.get("amount") or 0)
        already_paid = float(row.get("paid_amount") or 0)
        remaining = max(total - already_paid, 0)
        if amount > remaining:
            return False

        new_paid = already_paid + amount
        new_status = "paid" if new_paid >= total else "pending"

        dt_val = payment_date if payment_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if payment_date else dt_val

        upd_q = (
            f"UPDATE receivables SET paid_amount = {ph}, status = {ph}, paid_date = {dt_sql}, note = {ph} WHERE id = {ph}"
        )
        upd_note = note or row.get("note")
        upd_params = (new_paid, new_status, payment_date, upd_note, receivable_id) if payment_date else (new_paid, new_status, upd_note, receivable_id)
        cur.execute(upd_q, upd_params)

        tx_q = (
            f"INSERT INTO transactions (type, amount, category, description, date, product_id) "
            f"VALUES ('Receita', {ph}, 'Venda', {ph}, {dt_sql}, {ph})"
        )
        tx_desc = f"Recebimento de venda a prazo (parcela {row.get('installment_no')}/{row.get('total_installments')})"
        product_id = row.get("product_id")
        tx_params = (amount, tx_desc, payment_date, product_id) if payment_date else (amount, tx_desc, product_id)
        cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro receive_installment: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return False


def create_sale(
    product_id: int,
    quantity: int,
    unit_price: float,
    company_id: Optional[int] = None,
    partner_id: Optional[int] = None,
    description: Optional[str] = None,
    sale_date: Optional[str] = None,
    payment_mode: str = "avista",
    installments: int = 1,
    upfront_amount: float = 0.0,
    first_due_date: Optional[str] = None
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

        total = float(unit_price) * qty_sold
        if total <= 0:
            raise Exception("Valor total da venda inválido")

        payment_mode = (payment_mode or "avista").lower()
        if payment_mode not in ("avista", "parcelado", "aprazo"):
            payment_mode = "avista"

        upfront_amount = float(upfront_amount or 0)
        upfront_amount = min(max(upfront_amount, 0), total)

        if payment_mode == "avista":
            upfront_amount = total
            installments = 1
        elif payment_mode == "aprazo":
            installments = 1
        else:
            installments = max(int(installments or 1), 1)

        estimate = estimate_sale_cost(product_id, qty_sold)
        blended_unit_cost = float(estimate["estimated_unit_cost"])

        if _table_exists("product_cost_adjustments"):
            ph = "?" if DB_TYPE == "sqlite" else "%s"
            adjustments = _get_pending_cost_adjustments(product_id)
            for adj in adjustments:
                adj_id = int(adj["id"])
                rem_qty = int(adj["remaining_qty"] or 0)
                unit_inc = float(adj["unit_increment"] or 0)
                if rem_qty <= 0 or unit_inc <= 0:
                    continue
                alloc_qty = min(qty_sold, rem_qty)
                new_rem = rem_qty - alloc_qty
                cur.execute(
                    f"UPDATE product_cost_adjustments SET remaining_qty = {ph} WHERE id = {ph}",
                    (new_rem, adj_id)
                )

        ph = "?" if DB_TYPE == "sqlite" else "%s"
        cur.execute(
            f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference, unit_cost) VALUES ({ph}, {ph}, 'out', {ph}, {ph})",
            (product_id, qty_sold, description, blended_unit_cost)
        )

        dt_val = sale_date if sale_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if sale_date else dt_val

        tx_id = None
        if upfront_amount > 0:
            q = f"INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) VALUES ('Receita', {ph}, 'Venda', {ph}, {dt_sql}, {ph}, {ph}, {ph})"
            recv_desc = (description or "Venda") + f" [{payment_mode}]"
            params = (upfront_amount, recv_desc, sale_date, product_id, partner_id, company_id) if sale_date else (upfront_amount, recv_desc, product_id, partner_id, company_id)

            if DB_TYPE == "postgres":
                cur.execute(q + " RETURNING id", params)
                tx_id = cur.fetchone()[0]
            else:
                cur.execute(q, params)
                tx_id = cur.lastrowid

        pending_amount = max(total - upfront_amount, 0)
        if pending_amount > 0 and _table_exists("receivables"):
            from datetime import datetime, timedelta
            if first_due_date:
                base_due = datetime.fromisoformat(str(first_due_date)).date()
            elif sale_date:
                base_due = datetime.fromisoformat(str(sale_date)).date()
            else:
                base_due = datetime.now().date()

            inst_count = max(int(installments or 1), 1)
            part_value = round(pending_amount / inst_count, 2)
            values = [part_value] * inst_count
            diff = round(pending_amount - sum(values), 2)
            values[-1] = round(values[-1] + diff, 2)

            for idx, value in enumerate(values, start=1):
                if value <= 0:
                    continue
                due = base_due + timedelta(days=30 * (idx - 1))
                r_q = (
                    f"INSERT INTO receivables (product_id, sale_transaction_id, installment_no, total_installments, amount, due_date, status, paid_amount, note) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'pending', 0, {ph})"
                )
                r_note = f"Venda a receber - parcela {idx}/{inst_count}. {description or ''}".strip()
                cur.execute(r_q, (product_id, tx_id, idx, inst_count, value, str(due), r_note))

        conn.commit()
        cur.close()
        conn.close()
        return tx_id if tx_id else -1
    except Exception as e:
        print(f"Erro create_sale: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None


def create_credit_sale(
    product_id: int,
    quantity: int,
    unit_price: float,
    due_date: str,
    customer_name: Optional[str] = None,
    company_id: Optional[int] = None,
    partner_id: Optional[int] = None,
    description: Optional[str] = None,
    sale_date: Optional[str] = None
) -> Optional[int]:
    if not _table_exists("accounts_receivable") or not _table_exists("accounts_receivable_payments"):
        return None

    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        qty_sold = int(quantity)
        avail = get_stock_level(product_id)
        if avail < qty_sold:
            raise Exception(f"Estoque insuficiente ({avail})")

        estimate = estimate_sale_cost(product_id, qty_sold)
        blended_unit_cost = float(estimate["estimated_unit_cost"])
        total = float(unit_price) * qty_sold
        sale_note = (description or "").strip()
        customer = (customer_name or "").strip() or None

        if _table_exists("product_cost_adjustments"):
            ph = "?" if DB_TYPE == "sqlite" else "%s"
            adjustments = _get_pending_cost_adjustments(product_id)
            for adj in adjustments:
                adj_id = int(adj["id"])
                rem_qty = int(adj["remaining_qty"] or 0)
                unit_inc = float(adj["unit_increment"] or 0)
                if rem_qty <= 0 or unit_inc <= 0:
                    continue
                alloc_qty = min(qty_sold, rem_qty)
                new_rem = rem_qty - alloc_qty
                cur.execute(
                    f"UPDATE product_cost_adjustments SET remaining_qty = {ph} WHERE id = {ph}",
                    (new_rem, adj_id)
                )

        ph = "?" if DB_TYPE == "sqlite" else "%s"
        dt_val = sale_date if sale_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if sale_date else dt_val
        due_sql = ph
        recv_q = (
            f"INSERT INTO accounts_receivable "
            f"(product_id, partner_id, company_id, customer_name, description, quantity, unit_price, total_amount, received_amount, sale_date, due_date, status) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 0, {dt_sql}, {due_sql}, 'open')"
        )
        recv_params = (
            (product_id, partner_id, company_id, customer, sale_note, qty_sold, float(unit_price), total, sale_date, due_date)
            if sale_date else
            (product_id, partner_id, company_id, customer, sale_note, qty_sold, float(unit_price), total, due_date)
        )

        if DB_TYPE == "postgres":
            cur.execute(recv_q + " RETURNING id", recv_params)
            receivable_id = cur.fetchone()[0]
        else:
            cur.execute(recv_q, recv_params)
            receivable_id = cur.lastrowid

        reference = f"[ARSALE:{receivable_id}] {sale_note}".strip()
        cur.execute(
            f"INSERT INTO stock_movements (product_id, quantity, movement_type, reference, unit_cost) VALUES ({ph}, {ph}, 'out', {ph}, {ph})",
            (product_id, qty_sold, reference, blended_unit_cost)
        )

        tx_q = (
            f"INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) "
            f"VALUES ('Receita', {ph}, 'Venda a Prazo', {ph}, {dt_sql}, {ph}, {ph}, {ph})"
        )
        tx_params = (
            (total, reference, sale_date, product_id, partner_id, company_id)
            if sale_date else
            (total, reference, product_id, partner_id, company_id)
        )
        cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return receivable_id
    except Exception as e:
        print(f"Erro create_credit_sale: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None


def add_receivable_payment(
    receivable_id: int,
    amount: float,
    payment_date: Optional[str] = None,
    note: Optional[str] = None
) -> Optional[int]:
    if not _table_exists("accounts_receivable") or not _table_exists("accounts_receivable_payments"):
        return None

    payment_amount = float(amount or 0)
    if payment_amount <= 0:
        return None

    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        ph = "?" if DB_TYPE == "sqlite" else "%s"
        receivable_rows = run_query(
            "SELECT * FROM accounts_receivable WHERE id = %s",
            (receivable_id,)
        ) or []
        if not receivable_rows:
            raise Exception("Conta a receber não encontrada.")

        receivable = receivable_rows[0]
        total_amount = float(receivable.get("total_amount") or 0)
        received_amount = float(receivable.get("received_amount") or 0)
        remaining_amount = total_amount - received_amount
        if payment_amount > remaining_amount + 0.0001:
            raise Exception(f"Pagamento maior que o saldo pendente (R$ {remaining_amount:.2f}).")

        dt_val = payment_date if payment_date else ("date('now')" if DB_TYPE == "sqlite" else "CURRENT_DATE")
        dt_sql = ph if payment_date else dt_val
        pay_q = (
            f"INSERT INTO accounts_receivable_payments (receivable_id, amount, payment_date, note) "
            f"VALUES ({ph}, {ph}, {dt_sql}, {ph})"
        )
        pay_params = (receivable_id, payment_amount, payment_date, note) if payment_date else (receivable_id, payment_amount, note)

        if DB_TYPE == "postgres":
            cur.execute(pay_q + " RETURNING id", pay_params)
            payment_id = cur.fetchone()[0]
        else:
            cur.execute(pay_q, pay_params)
            payment_id = cur.lastrowid

        new_received = received_amount + payment_amount
        new_status = "paid" if new_received >= total_amount - 0.0001 else "partial"
        cur.execute(
            f"UPDATE accounts_receivable SET received_amount = {ph}, status = {ph} WHERE id = {ph}",
            (new_received, new_status, receivable_id)
        )

        tx_desc = f"[ARPAY:{payment_id}|ARSALE:{receivable_id}] {note or receivable.get('description') or ''}".strip()
        tx_q = (
            f"INSERT INTO transactions (type, amount, category, description, date, product_id, partner_id, company_id) "
            f"VALUES ('Receita', {ph}, 'Recebimento Venda a Prazo', {ph}, {dt_sql}, {ph}, {ph}, {ph})"
        )
        tx_params = (
            (payment_amount, tx_desc, payment_date, receivable.get("product_id"), receivable.get("partner_id"), receivable.get("company_id"))
            if payment_date else
            (payment_amount, tx_desc, receivable.get("product_id"), receivable.get("partner_id"), receivable.get("company_id"))
        )
        cur.execute(tx_q, tx_params)

        conn.commit()
        cur.close()
        conn.close()
        return payment_id
    except Exception as e:
        print(f"Erro add_receivable_payment: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
        return None


def get_accounts_receivable_summary() -> Dict[str, Any]:
    if not _table_exists("accounts_receivable"):
        return {
            "open_amount": 0.0,
            "overdue_amount": 0.0,
            "total_open_titles": 0,
            "items": [],
        }

    outstanding_expr = "(ar.total_amount - ar.received_amount)"
    if DB_TYPE == "postgres":
        overdue_sql = f"CASE WHEN ar.due_date IS NOT NULL AND ar.due_date < CURRENT_DATE THEN {outstanding_expr} ELSE 0 END"
    else:
        overdue_sql = f"CASE WHEN ar.due_date IS NOT NULL AND ar.due_date < date('now') THEN {outstanding_expr} ELSE 0 END"

    query = f"""
    SELECT
        ar.id,
        ar.customer_name,
        ar.description,
        ar.quantity,
        ar.unit_price,
        ar.total_amount,
        ar.received_amount,
        {outstanding_expr} AS outstanding_amount,
        ar.sale_date,
        ar.due_date,
        ar.status,
        p.name AS product_name,
        {overdue_sql} AS overdue_amount
    FROM accounts_receivable ar
    LEFT JOIN products p ON p.id = ar.product_id
    WHERE (ar.total_amount - ar.received_amount) > 0
    ORDER BY
        CASE WHEN ar.due_date IS NULL THEN 1 ELSE 0 END,
        ar.due_date ASC,
        ar.id DESC
    """
    items = run_query(query) or []
    for item in items:
        item["outstanding_amount"] = float(item.get("outstanding_amount") or 0)
        item["overdue_amount"] = float(item.get("overdue_amount") or 0)
        item["received_amount"] = float(item.get("received_amount") or 0)
        item["total_amount"] = float(item.get("total_amount") or 0)
        item["unit_price"] = float(item.get("unit_price") or 0)

    return {
        "open_amount": sum(item["outstanding_amount"] for item in items),
        "overdue_amount": sum(item["overdue_amount"] for item in items),
        "total_open_titles": len(items),
        "items": items,
    }

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
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Receita' AND COALESCE(category,'') NOT IN (""" + NON_OPERATIONAL_SQL + """) AND """ + NON_OPERATIONAL_EXCLUSION_SQL + """) AS total_revenue,
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='Despesa' AND COALESCE(category,'') NOT IN (""" + PROFIT_EXPENSE_EXCLUSIONS_SQL + """) AND """ + NON_OPERATIONAL_EXCLUSION_SQL + """) AS total_expenses,
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

    receivable_open_total = 0.0
    if _table_exists("accounts_receivable"):
        receivable_rows = run_query(
            "SELECT COALESCE(SUM(total_amount - received_amount), 0) AS total FROM accounts_receivable WHERE (total_amount - received_amount) > 0"
        ) or []
        receivable_open_total = float(receivable_rows[0].get("total", 0) or 0) if receivable_rows else 0.0
    
    for r in res:
        # Lucro real = Receita - Despesas - CMV
        lucro_real = float(r['total_revenue']) - float(r['total_expenses']) - cmv_total
        share_ratio = float(r['share_pct']) / 100.0
        # Cota do sócio no lucro operacional
        r['share_of_profit'] = lucro_real * share_ratio
        # Parte do lucro ainda "presa" em vendas a prazo abertas.
        r['pending_receivable_balance'] = receivable_open_total * share_ratio
        # Saldo teórico total = lucro + aportes - retiradas.
        r['current_balance'] = r['share_of_profit'] + float(r['total_contributed']) - float(r['total_withdrawn'])
        # Saldo disponível = saldo total menos a fatia ainda não recebida do contas a receber.
        r['available_balance'] = r['current_balance'] - r['pending_receivable_balance']
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
        COALESCE(SUM(CASE WHEN type='Receita' AND COALESCE(category,'') NOT IN ({NON_OPERATIONAL_SQL}) AND {NON_OPERATIONAL_EXCLUSION_SQL} THEN amount ELSE 0 END), 0) AS revenue,
        COALESCE(SUM(CASE WHEN type='Despesa' AND COALESCE(category,'') NOT IN ({PROFIT_EXPENSE_EXCLUSIONS_SQL}) AND {NON_OPERATIONAL_EXCLUSION_SQL} THEN amount ELSE 0 END), 0) AS expenses,
        COALESCE(SUM(CASE WHEN type='Despesa' AND COALESCE(category,'') IN ({INFRA_INVESTMENT_SQL}) THEN amount ELSE 0 END), 0) AS infra_investment
    FROM transactions WHERE {filter_sql}"""
    
    # Saldo total do caixa: todas as receitas - todas as despesas + aportes de sócios - retiradas de sócios
    q_cash = """
    SELECT 
        (
            SELECT COALESCE(SUM(
                CASE
                    WHEN type='Receita' AND COALESCE(category, '') = 'Venda a Prazo' THEN 0
                    WHEN type='Receita' THEN amount
                    ELSE -amount
                END
            ), 0)
            FROM transactions
        )
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
        estimate = estimate_sale_cost(int(r['id']), 1)
        pending_total = float(estimate['pending_adjustment_total'])
        base_cost = float(r['last_cost'] or 0)
        effective_unit_cost = float(estimate['estimated_unit_cost'] or base_cost)
        price = float(r['price'] or 0)
        # Para indicadores de estoque, só conta o que está disponível hoje.
        r['last_cost'] = effective_unit_cost
        r['total_cost_value'] = (base_cost * qty) + pending_total
        r['total_sale_value'] = price * qty
        r['stock_qty'] = qty
    return res

def get_revenue_details():
    res = run_query(
        "SELECT CASE WHEN product_id IS NOT NULL THEN 'Venda' ELSE 'Servico' END as channel, SUM(amount) as total "
        "FROM transactions "
        f"WHERE type = 'Receita' AND COALESCE(category,'') NOT IN ({NON_OPERATIONAL_SQL}) AND {NON_OPERATIONAL_EXCLUSION_SQL} "
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

    if source == "receivable":
        if not _table_exists("accounts_receivable") or not _table_exists("accounts_receivable_payments"):
            return False
        payments = run_query(
            "SELECT id FROM accounts_receivable_payments WHERE receivable_id = %s LIMIT 1",
            (record_id,)
        ) or []
        if payments:
            return False

        recv_rows = run_query(
            "SELECT id, product_id, description FROM accounts_receivable WHERE id = %s",
            (record_id,)
        ) or []
        if not recv_rows:
            return False
        recv = recv_rows[0]
        ref = f"[ARSALE:{record_id}] {recv.get('description') or ''}".strip()

        if recv.get("product_id"):
            mv = run_query(
                "SELECT id FROM stock_movements WHERE product_id = %s AND movement_type='out' AND reference = %s ORDER BY id DESC LIMIT 1",
                (recv["product_id"], ref)
            ) or []
            if mv:
                run_query("DELETE FROM stock_movements WHERE id = %s", (mv[0]["id"],))

        run_query(
            "DELETE FROM transactions WHERE category = 'Venda a Prazo' AND description LIKE %s",
            (f"[ARSALE:{record_id}]%",)
        )
        res = run_query("DELETE FROM accounts_receivable WHERE id = %s", (record_id,))
        return res is True

    if source == "receivable_payment":
        if not _table_exists("accounts_receivable") or not _table_exists("accounts_receivable_payments"):
            return False
        pay_rows = run_query(
            "SELECT id, receivable_id, amount FROM accounts_receivable_payments WHERE id = %s",
            (record_id,)
        ) or []
        if not pay_rows:
            return False
        pay = pay_rows[0]

        recv_rows = run_query(
            "SELECT total_amount, received_amount FROM accounts_receivable WHERE id = %s",
            (pay["receivable_id"],)
        ) or []
        if not recv_rows:
            return False
        recv = recv_rows[0]
        new_received = max(float(recv.get("received_amount") or 0) - float(pay.get("amount") or 0), 0.0)
        total_amount = float(recv.get("total_amount") or 0)
        new_status = "open" if new_received <= 0 else ("paid" if new_received >= total_amount - 0.0001 else "partial")
        run_query(
            "UPDATE accounts_receivable SET received_amount = %s, status = %s WHERE id = %s",
            (new_received, new_status, pay["receivable_id"])
        )
        run_query(
            "DELETE FROM transactions WHERE category = 'Recebimento Venda a Prazo' AND description LIKE %s",
            (f"[ARPAY:{record_id}|ARSALE:{pay['receivable_id']}]%",)
        )
        res = run_query("DELETE FROM accounts_receivable_payments WHERE id = %s", (record_id,))
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
        WHERE COALESCE(category, '') NOT IN ('Empréstimo Sócios', 'Amortização Empréstimo', 'Estoque/Custo Adicional', 'Venda a Prazo', 'Recebimento Venda a Prazo')
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

    if _table_exists("accounts_receivable"):
        parts.append(
            """
            SELECT
                ar.id,
                CAST(ar.sale_date AS TEXT) as date,
                'Venda a Prazo' as type,
                ar.total_amount as amount,
                'Venda a Prazo' as category,
                COALESCE(p.name, 'Produto Removido') || ' | Cliente: ' || COALESCE(ar.customer_name, 'Nao informado') || ' | ' || COALESCE(ar.description, '') as description,
                'receivable' as source,
                ar.id as source_id
            FROM accounts_receivable ar
            LEFT JOIN products p ON p.id = ar.product_id
            """
        )

    if _table_exists("accounts_receivable_payments") and _table_exists("accounts_receivable"):
        parts.append(
            """
            SELECT
                pay.id,
                CAST(pay.payment_date AS TEXT) as date,
                'Recebimento a Prazo' as type,
                pay.amount as amount,
                'Recebimento Venda a Prazo' as category,
                COALESCE(p.name, 'Produto Removido') || ' | Cliente: ' || COALESCE(ar.customer_name, 'Nao informado') || ' | ' || COALESCE(pay.note, ar.description, '') as description,
                'receivable_payment' as source,
                pay.id as source_id
            FROM accounts_receivable_payments pay
            LEFT JOIN accounts_receivable ar ON ar.id = pay.receivable_id
            LEFT JOIN products p ON p.id = ar.product_id
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
        qty = max(int(r['current_stock'] or 0), 0)
        estimate = estimate_sale_cost(int(r['id']), 1)
        pending_total = float(estimate['pending_adjustment_total'])
        base_cost = float(r['last_cost'] or 0)
        r['last_cost'] = float(estimate['estimated_unit_cost'] or base_cost)
        r['stock_value_cost'] = (base_cost * qty) + pending_total
        r['stock_value_sale'] = float(r['price']) * int(r['current_stock'])
    return res
