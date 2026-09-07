import streamlit as st
import pandas as pd
from datetime import date
import calendar
import plotly.express as px
import plotly.graph_objects as go
import io
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path, override=True)

from database import run_query, save_transactions_batch, init_db
from ai_agent import process_chat_command, generate_ai_reply, process_statement, set_api_key_permanent
from db_helpers import (
    create_company, get_companies,
    create_partner, get_partners, update_partner_share,
    create_product, get_products,
    add_stock_movement, get_stock_level,
    get_expense_types, get_income_types,
    create_sale, create_credit_sale, add_receivable_payment,
    create_contribution, create_withdrawal, create_product_cost_adjustment,
    create_partner_loan, add_partner_loan_payment, get_partner_loans, get_partner_loans_summary,
    get_partner_loan_installments,
    get_partner_reports, get_advanced_kpis, get_upcoming_alerts,
    get_receivables_summary, receive_installment, create_fixed_expense,
    get_inventory_report, get_revenue_details, get_infra_inventory, get_accounts_receivable_summary,
    estimate_sale_cost,
    delete_history_item, get_all_transactions, get_detailed_stock_report,
    get_categories, create_category,
    find_product_by_barcode, add_product_barcode, get_product_barcodes, delete_product_barcode,
    normalize_barcode, create_consignment_supplier, get_consignment_suppliers,
    get_consignment_payables, pay_consignment_payable, create_salesperson,
    get_salespeople, get_salesperson_commissions, pay_salesperson_commission,
    add_salesperson_bonus, get_monthly_payables, pay_monthly_payable,
    create_company_asset, get_company_assets, get_company_assets_summary,
    get_chat_insight_context
)
from backup_utils import export_backup, import_backup
import os

def add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

st.set_page_config(page_title="Agente Financeiro", page_icon="💰", layout="wide")

# ... (sidebar debug code) ...

# Garante criação/migração de tabelas na primeira execução da sessão.
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.title("💰 Agente Financeiro Inteligente")

# Abas para separar Chat, Lançamentos, Dashboard, Histórico, Importação e Gerenciamento
tab1, tab_manual, tab2, tab_stock, tab_history, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📝 Lançamentos", "📊 Dashboard", "📦 Estoque", "📜 Histórico", "📂 Importar", "⚙️ Gerenciar", "📤 Exportar"])

# --- TAB 1: CHAT ---
with tab1:
    col_chat, col_info = st.columns([2, 1])
    
    with col_info:
        st.subheader("🔎 Insights financeiros")
        st.info("Este chat é somente leitura. Pergunte sobre gastos, receitas, lucro, juros, combustível, contas a pagar, consignados ou comissões.")
        intent_option = "Consultar dados"
        
        intent_map = {"Consultar dados": "FINANCIAL_INSIGHT"}
        selected_label = intent_option
        selected_intent = intent_map[selected_label]
        
        # Dicas dinâmicas
        hints = {"FINANCIAL_INSIGHT": "Ex: 'Quanto gastei com juros este mês?' ou 'Quanto paguei de combustível?'"}
        st.info("💡 " + hints[selected_intent])

    with col_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "current_action" not in st.session_state:
            st.session_state.current_action = None

        # Exibir histórico
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Hint logo acima do box de texto
        st.caption(f"✨ Selecionado: {selected_label}. {hints[selected_intent]}")

        # Input do usuário
        if prompt := st.chat_input("Digite sua mensagem aqui..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Limpa o input visualmente (a execução continua)
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    insight_context = get_chat_insight_context()
                    ai_res = process_chat_command(prompt, context_data=insight_context)
                    st.session_state.current_action = ai_res
                    reply = generate_ai_reply(ai_res)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    if "error" in ai_res:
                        st.error(reply)
                    else:
                        st.markdown(reply)

    # Área de confirmação (só aparece quando a IA diz que está COMPLETE)
    # O chat é somente leitura; lançamentos devem ser feitos nas telas operacionais.
    if False and st.session_state.current_action and st.session_state.current_action.get("status") == "COMPLETE":
        action = st.session_state.current_action
        intent = action["intent"]
        data = action["data"]
        
        with st.expander(f"📝 Confirmar Lançamento: {intent}", expanded=True):
            st.json(data) # Mostra os dados que serão salvos
            
            if st.button("✅ Confirmar e Salvar"):
                success = False
                try:
                    # Se for STOCK_MOVEMENT ou REGISTER_SALE e o product_id estiver nulo, cria o produto antes
                    p_id = data.get("product_id")
                    if not p_id and intent in ["STOCK_MOVEMENT", "REGISTER_SALE"]:
                        comps = get_companies()
                        comp_id = comps[0]['id'] if comps else create_company("Minha Empresa")
                        p_id = create_product(
                            company_id=comp_id,
                            name=data.get("description", "Produto Novo"),
                            price=data.get("amount", 0.0) / data.get("quantity", 1) if data.get("quantity", 1) > 0 else data.get("amount", 0.0)
                        )
                        data["product_id"] = p_id

                    if intent == "SAVE_TRANSACTION":
                        q = "INSERT INTO transactions (type, amount, category, description, date) VALUES (%s,%s,%s,%s,%s)"
                        params = (data.get("type"), data.get("amount"), data.get("category"), data.get("description"), data.get("date"))
                        success = run_query(q, params)
                    
                    elif intent == "REGISTER_SALE":
                        if p_id:
                            # Usa o helper de venda que já baixa estoque.
                            sale_kwargs = dict(
                                product_id=p_id,
                                quantity=data.get("quantity", 1),
                                unit_price=data.get("amount", 0) / data.get("quantity", 1) if data.get("quantity", 1) > 0 else 0,
                                description=data.get("description"),
                                sale_date=data.get("date")
                            )
                            if data.get("source") == "consignado":
                                sale_kwargs.update(
                                    inventory_source="consignado",
                                    consignment_supplier_id=data.get("consignment_supplier_id"),
                                    consignment_unit_amount=float(data.get("consignment_unit_amount") or 0),
                                    salesperson_id=data.get("salesperson_id"),
                                    commission_pct=float(data.get("commission_pct") or 0),
                                    delivery_cost=float(data.get("delivery_cost") or 0),
                                    agreed_commission_amount=float(data.get("agreed_commission_amount") or 0),
                                    bonus_amount=float(data.get("bonus_amount") or 0)
                                )
                            elif data.get("salesperson_id"):
                                sale_kwargs.update(
                                    salesperson_id=data.get("salesperson_id"),
                                    commission_pct=float(data.get("commission_pct") or 0),
                                    delivery_cost=float(data.get("delivery_cost") or 0),
                                    agreed_commission_amount=float(data.get("agreed_commission_amount") or 0),
                                    bonus_amount=float(data.get("bonus_amount") or 0)
                                )
                            if data.get("payment_mode") == "credit":
                                sale_kwargs["description"] = (
                                    f"{sale_kwargs.get('description') or 'Venda'} | Cliente: {data.get('customer_name') or 'Não informado'}"
                                )
                                res = create_sale(
                                    **sale_kwargs,
                                    payment_mode="aprazo",
                                    upfront_amount=0,
                                    first_due_date=data.get("due_date") or data.get("date")
                                )
                            else:
                                res = create_sale(**sale_kwargs)
                            success = res is not None
                        else:
                            st.error("Produto não identificado. Tente dizer o nome correto do produto ou crie-o primeiro.")
                            success = False
                    
                    elif intent == "PARTNER_CONTRIBUTION":
                        res = create_contribution(data.get("partner_id"), data.get("amount"), data.get("date"), data.get("description"))
                        success = res is not None
                        
                    elif intent == "PARTNER_WITHDRAWAL":
                        res = create_withdrawal(data.get("partner_id"), data.get("amount"), data.get("date"), data.get("description"))
                        success = res is not None

                    elif intent == "CREATE_PRODUCT":
                        # Garantir que temos uma empresa
                        companies = get_companies()
                        comp_id = companies[0]['id'] if companies else create_company("Minha Empresa")
                        
                        p_id = create_product(
                            company_id=comp_id,
                            name=data.get("description") or data.get("product_name"),
                            price=data.get("amount", 0)
                        )
                        if p_id and data.get("quantity", 0) > 0:
                            add_stock_movement(
                                product_id=p_id,
                                quantity=data.get("quantity"),
                                movement_type='in',
                                reference="Saldo inicial",
                                source=data.get("source", "próprio"),
                                is_paid=data.get("is_paid", False),
                                unit_cost=data.get("amount", 0),
                                consignment_supplier_id=data.get("consignment_supplier_id")
                            )
                        success = p_id is not None

                    elif intent == "STOCK_MOVEMENT":
                        if p_id:
                            # Identifica tipo de movimento da IA ou assume 'in' se for compra/chegada
                            m_type = data.get("type", "in")
                            qty = int(data.get("quantity", 1))
                            
                            res = add_stock_movement(
                                product_id=p_id,
                                quantity=qty,
                                movement_type=m_type,
                                reference=data.get("description"),
                                source=data.get("source", "próprio"),
                                is_paid=data.get("is_paid", False),
                                unit_cost=float(data.get("amount", 0)) / qty if qty > 0 else 0,
                                consignment_supplier_id=data.get("consignment_supplier_id")
                            )
                            success = res is not None
                        else:
                            st.error("Produto não identificado. Tente dizer o nome correto do produto.")
                            success = False

                    if success:
                        st.success("Lançamento realizado com sucesso!")
                        st.session_state.current_action = None
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

            if st.button("❌ Cancelar"):
                st.session_state.current_action = None
                st.rerun()

# --- TAB: LANÇAMENTOS (MANUAL) ---
with tab_manual:
    st.header("📝 Lançamentos Manuais")
    st.info("Utilize os formulários abaixo para registros rápidos sem o uso do chat.")
    
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🛒 Venda", "💰 Financeiro", "📦 Estoque", "👥 Sócios"])
    
    with sub_tab1:
        st.subheader("Registrar Venda")
        prods = get_products()
        if not prods:
            st.warning("Nenhum produto cadastrado. Vá em 'Estoque' para criar produtos.")
        else:
            prods_dict = {p['id']: p for p in prods}
            p_options = {
                f"{p['name']} (ID {p['id']} - R$ {float(p['price']):.2f})": p['id']
                for p in prods
            }
            sale_barcode = normalize_barcode(st.text_input(
                "Código de barras",
                key="sale_barcode_scan",
                placeholder="Escaneie ou digite o código e pressione Enter"
            ))
            sale_scan_product = find_product_by_barcode(sale_barcode) if sale_barcode else None
            if sale_barcode and not sale_scan_product:
                st.warning("Código não encontrado. Cadastre o produto ou associe este código em Gerenciar > Produtos e Estoque.")
            elif sale_scan_product:
                st.success(f"Produto localizado: {sale_scan_product['name']} (ID {sale_scan_product['id']})")

            product_labels = list(p_options.keys())
            default_sale_label = "-"
            if sale_scan_product:
                default_sale_label = next(
                    (label for label, pid in p_options.items() if int(pid) == int(sale_scan_product["id"])),
                    "-"
                )
            selected_p = st.selectbox(
                "Selecione o Produto",
                options=["-"] + product_labels,
                index=(["-"] + product_labels).index(default_sale_label) if default_sale_label in ["-"] + product_labels else 0
            )
            
            if selected_p != "-":
                p_id = p_options[selected_p]
                p_obj = prods_dict[p_id]

                sale_origin = st.radio(
                    "Origem do estoque",
                    ["Próprio", "Consignado"],
                    horizontal=True,
                    key="sale_origin"
                )
                consignment_supplier_id = None
                consignment_unit_amount = 0.0
                if sale_origin == "Consignado":
                    suppliers = get_consignment_suppliers()
                    supplier_options = {"-": None}
                    supplier_options.update({f"{s['name']} (ID {s['id']})": int(s['id']) for s in suppliers})
                    selected_supplier = st.selectbox("Fornecedor consignante", options=list(supplier_options.keys()), key="sale_supplier")
                    consignment_supplier_id = supplier_options[selected_supplier]
                    consignment_unit_amount = st.number_input(
                        "Valor unitário a repassar ao consignante (R$)",
                        min_value=0.01,
                        step=0.01,
                        value=0.01,
                        key="sale_consignment_amount",
                        help="Este valor vira uma conta a pagar quando a venda for registrada."
                    )

                salespeople_sale = get_salespeople()
                salesperson_options = {"-": None}
                salesperson_options.update({f"{s['name']} (ID {s['id']})": int(s['id']) for s in salespeople_sale})
                selected_salesperson = st.selectbox("Vendedora", options=list(salesperson_options.keys()), key="sale_salesperson")
                salesperson_id = salesperson_options[selected_salesperson]
                salesperson_obj = next((s for s in salespeople_sale if int(s['id']) == int(salesperson_id)), None) if salesperson_id else None
                commission_pct = st.number_input(
                    "Comissão sobre o lucro bruto (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(salesperson_obj.get('default_commission_pct', 0)) if salesperson_obj else 0.0,
                    step=0.1,
                    key="sale_commission_pct",
                    disabled=not bool(salesperson_id)
                )
                agreed_commission_amount = st.number_input(
                    "Valor combinado da comissão (R$) - opcional",
                    min_value=0.0,
                    step=0.01,
                    value=0.0,
                    key="sale_agreed_commission",
                    disabled=not bool(salesperson_id),
                    help="Se informado, substitui o cálculo percentual sobre o lucro bruto."
                )
                sale_bonus_amount = st.number_input(
                    "Bônus extra da venda (R$)",
                    min_value=0.0,
                    step=0.01,
                    value=0.0,
                    key="sale_bonus_amount",
                    disabled=not bool(salesperson_id),
                    help="O bônus aumenta a comissão e reduz o lucro líquido desta operação."
                )
                has_delivery_cost = st.checkbox("Esta venda tem custo de entrega?", key="sale_has_delivery")
                delivery_cost = 0.0
                if has_delivery_cost:
                    delivery_cost = st.number_input(
                        "Valor da entrega (R$)",
                        min_value=0.01,
                        step=0.01,
                        value=0.01,
                        key="sale_delivery_cost",
                        help="Será lançado como despesa da venda e reduzirá o lucro bruto."
                    )
                
                col_v1, col_v2 = st.columns(2)
                qty_venda = col_v1.number_input("Quantidade", min_value=1, value=1, key="v_qty")
                preco_venda = col_v2.number_input(
                    "Preço Unit. de Venda (R$)",
                    min_value=0.01, step=0.01,
                    value=float(p_obj['price']),
                    help="Pode alterar o preço para esta venda específica."
                )
                
                # Preview do lucro já considerando custos adicionais vinculados ao produto.
                custo_estimado = estimate_sale_cost(p_id, qty_venda)
                ultimo_custo = float(custo_estimado.get('estimated_unit_cost') or 0.0)
                if sale_origin == "Consignado":
                    ultimo_custo = float(consignment_unit_amount or 0.0)
                total_venda = preco_venda * qty_venda
                custo_produto_venda = ultimo_custo * qty_venda
                custo_total_venda = custo_produto_venda + float(delivery_cost or 0)
                lucro_bruto = total_venda - custo_total_venda
                comissao_base = float(agreed_commission_amount or 0) if float(agreed_commission_amount or 0) > 0 else max(lucro_bruto, 0) * float(commission_pct or 0) / 100
                comissao_prevista = comissao_base + float(sale_bonus_amount or 0)
                lucro_liquido = lucro_bruto - comissao_prevista
                
                col_i1, col_i2 = st.columns(2)
                col_i1.info(f"💰 **Total da Venda:** R$ {total_venda:.2f}")
                if ultimo_custo > 0:
                    col_i2.success(f"📈 **Lucro desta venda:** R$ {lucro_bruto:.2f}")
                    if float(custo_estimado.get('extra_cost_total') or 0.0) > 0:
                        st.caption(
                            f"Custo total desta venda: R$ {custo_total_venda:.2f} "
                            f"(inclui R$ {float(custo_estimado.get('extra_cost_total') or 0.0):.2f} de despesas vinculadas)."
                        )
                if salesperson_id:
                    st.caption(f"Comissão prevista para {salesperson_obj['name']}: R$ {comissao_prevista:.2f} | Lucro líquido: R$ {lucro_liquido:.2f}")
                
                col_d1, col_d2 = st.columns(2)
                data_venda = col_d1.date_input("Data da Venda", value=date.today(), key="v_data")
                desc_venda = col_d2.text_input("Observação (opcional)", placeholder="Ex: Venda balcão")

                modalidade_venda = st.radio(
                    "Modalidade",
                    ["À vista", "A prazo"],
                    horizontal=True,
                    key="sale_mode"
                )

                customer_name = ""
                due_date = data_venda
                if modalidade_venda == "A prazo":
                    col_c1, col_c2 = st.columns(2)
                    customer_name = col_c1.text_input("Cliente / referência", placeholder="Ex: João, Pedido #123")
                    due_date = col_c2.date_input("Vencimento", value=data_venda, key="credit_due_date")
                    saldo_resumo = get_accounts_receivable_summary()
                    st.caption(
                        f"Saldo atual a receber: R$ {float(saldo_resumo.get('open_amount', 0)):.2f} "
                        f"em {int(saldo_resumo.get('total_open_titles', 0))} título(s)."
                    )
                
                st.divider()
                cond_pag = st.radio(
                    "Forma de recebimento",
                    options=["À vista", "Parcelado", "A prazo (fiado)"],
                    horizontal=True,
                    help="À vista: entra no caixa agora. Parcelado/A prazo: registra contas a receber."
                )
                parcelas = 1
                entrada = total_venda
                primeira_parcela = data_venda

                if cond_pag == "Parcelado":
                    col_p1, col_p2 = st.columns(2)
                    parcelas = col_p1.number_input("Qtd. parcelas", min_value=2, max_value=24, value=2, step=1)
                    entrada = col_p2.number_input(
                        "Entrada recebida agora (R$)",
                        min_value=0.0,
                        max_value=float(total_venda),
                        value=0.0,
                        step=0.01
                    )
                    primeira_parcela = st.date_input("1º vencimento", value=data_venda, key="primeira_parcela")
                elif cond_pag == "A prazo (fiado)":
                    col_ap1, col_ap2 = st.columns(2)
                    entrada = col_ap1.number_input(
                        "Valor recebido agora (R$)",
                        min_value=0.0,
                        max_value=float(total_venda),
                        value=0.0,
                        step=0.01,
                        help="Se recebeu uma parte, informe aqui. O restante ficará pendente."
                    )
                    primeira_parcela = col_ap2.date_input("Vencimento", value=data_venda, key="venc_aprazo")

                if st.button("🚀 Registrar Venda", use_container_width=True):

                    modo = "avista"
                    if cond_pag == "Parcelado":
                        modo = "parcelado"
                    elif cond_pag == "A prazo (fiado)" or modalidade_venda == "A prazo":
                        modo = "aprazo"

                    res = create_sale(
                        p_id,
                        qty_venda,
                        preco_venda,
                        description=desc_venda,
                        sale_date=str(data_venda),
                        payment_mode=modo,
                        installments=int(parcelas),
                        upfront_amount=float(entrada),
                        first_due_date=str(primeira_parcela),
                        inventory_source="consignado" if sale_origin == "Consignado" else "próprio",
                        consignment_supplier_id=consignment_supplier_id,
                        consignment_unit_amount=float(consignment_unit_amount),
                        salesperson_id=salesperson_id,
                        commission_pct=float(commission_pct),
                        delivery_cost=float(delivery_cost),
                        agreed_commission_amount=float(agreed_commission_amount),
                        bonus_amount=float(sale_bonus_amount)
                    )
                    if res is not None:
                        pendente = max(float(total_venda) - float(entrada), 0)
                        if pendente > 0:
                            st.success(f"✅ Venda registrada! Recebido agora: R$ {float(entrada):.2f} | A receber: R$ {pendente:.2f}")
                        else:
                            st.success(f"✅ Venda de R$ {total_venda:.2f} registrada à vista!")
                        st.rerun()
                    else:
                        st.error("Erro ao registrar venda. Verifique o estoque disponível e os dados informados.")

        st.divider()
        st.subheader("Receber Venda a Prazo")
        receivable_summary = get_accounts_receivable_summary()
        open_titles = receivable_summary.get("items", [])
        if open_titles:
            receivable_options = {
                f"[{ 'LEG' if item.get('legacy_source') == 'receivables' else 'AR' }] #{item['id']} | {item.get('product_name') or 'Produto'} | Cliente: {item.get('customer_name') or 'Não informado'} | "
                f"Saldo: R$ {float(item.get('outstanding_amount') or 0):.2f} | Vence: {item.get('due_date') or 'Sem vencimento'}": item
                for item in open_titles
            }
            selected_receivable_label = st.selectbox(
                "Título em aberto",
                options=list(receivable_options.keys()),
                key="receivable_select"
            )
            selected_receivable = receivable_options[selected_receivable_label]
            max_receivable_amount = float(selected_receivable.get("outstanding_amount") or 0)

            col_r1, col_r2, col_r3 = st.columns(3)
            payment_input_kwargs = {
                "label": "Valor recebido (R$)",
                "min_value": 0.01,
                "value": max_receivable_amount if max_receivable_amount > 0 else 0.01,
                "step": 0.01,
                "key": "receivable_payment_amount",
            }
            if max_receivable_amount > 0:
                payment_input_kwargs["max_value"] = max_receivable_amount
            payment_amount = col_r1.number_input(**payment_input_kwargs)
            payment_date = col_r2.date_input("Data do recebimento", value=date.today(), key="receivable_payment_date")
            payment_note = col_r3.text_input("Nota", placeholder="Ex: Pix recebido", key="receivable_payment_note")

            if st.button("💸 Registrar Recebimento", use_container_width=True):
                if selected_receivable.get("legacy_source") == "receivables":
                    payment_id = receive_installment(
                        int(selected_receivable["id"]),
                        payment_amount,
                        payment_date=str(payment_date),
                        note=payment_note
                    )
                else:
                    payment_id = add_receivable_payment(
                        int(selected_receivable["id"]),
                        payment_amount,
                        payment_date=str(payment_date),
                        note=payment_note
                    )
                if payment_id:
                    st.success("Recebimento registrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Não foi possível registrar o recebimento. Revise o valor informado.")
        else:
            st.info("Nenhuma venda a prazo em aberto no momento.")

    with sub_tab2:
        st.subheader("Receber Vendas a Prazo")
        receivables_rows = run_query(
            "SELECT id, installment_no, total_installments, amount, paid_amount, due_date, note FROM receivables WHERE status='pending' ORDER BY due_date, id"
        ) or []
        if receivables_rows:
            recibo_op = {
                f"#{r['id']} | Parcela {r['installment_no']}/{r['total_installments']} | Venc: {r['due_date']} | Pendente: R$ {float(r['amount']) - float(r.get('paid_amount') or 0):.2f}": r
                for r in receivables_rows
            }
            sel_rec = st.selectbox("Parcela pendente", options=list(recibo_op.keys()))
            rec_obj = recibo_op[sel_rec]
            rec_pendente = max(float(rec_obj['amount']) - float(rec_obj.get('paid_amount') or 0), 0.0)
            col_rr1, col_rr2 = st.columns(2)
            valor_receb = col_rr1.number_input("Valor recebido desta parcela (R$)", min_value=0.01, max_value=float(rec_pendente), value=float(rec_pendente), step=0.01)
            data_receb = col_rr2.date_input("Data do recebimento", value=date.today(), key="dt_receb_parcela")
            if st.button("💸 Dar baixa / receber", use_container_width=True):
                ok = receive_installment(int(rec_obj['id']), float(valor_receb), payment_date=str(data_receb), note="Recebimento manual")
                if ok:
                    st.success("Recebimento lançado com sucesso.")
                    st.rerun()
                else:
                    st.error("Não foi possível registrar o recebimento da parcela.")
        else:
            st.info("Nenhuma venda pendente para receber.")

        st.divider()
        st.subheader("Nova Receita ou Despesa")
        tipo_f = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
        valor_f = st.number_input("Valor (R$)", min_value=0.01, step=0.01)

        # Atalho para custo adicional de produto (impacta CMV futuro)
        prods_fin = get_products()
        vincular_produto = st.checkbox(
            "Vincular despesa a um produto (Custo adicional / CMV)",
            key="fin_link_product",
            disabled=(tipo_f != "Despesa"),
            help="Use para reparo, componente, frete, etc. Este valor será absorvido no CMV das próximas vendas do produto."
        )
        prod_fin_label = "-"
        if vincular_produto and tipo_f == "Despesa":
            if prods_fin:
                prod_fin_label = st.selectbox(
                    "Produto do custo",
                    options=["-"] + [f"{p['id']} - {p['name']}" for p in prods_fin],
                    key="fin_product_target"
                )
            else:
                st.warning("Nenhum produto cadastrado para vincular custo.")
        
        # Dropdown dinâmico de categorias
        cats_disponiveis = get_categories(tipo_f)
        opcao_cat = st.selectbox(
            "Categoria",
            options=cats_disponiveis + ["➕ Criar nova categoria..."],
            help="Selecione uma categoria existente ou crie uma nova."
        )
        
        cat_f = opcao_cat
        if opcao_cat == "➕ Criar nova categoria...":
            nova_cat = st.text_input("Nome da nova categoria", placeholder="Ex: Marketing, Energia, Consultoria")
            cat_f = nova_cat
        
        desc_f = st.text_area("Descrição", placeholder="Detalhes do lançamento...")
        data_f = st.date_input("Data", value=date.today())
        
        if st.button("➕ Salvar no Financeiro", use_container_width=True):
            if not cat_f or cat_f == "➕ Criar nova categoria...":
                st.warning("Por favor, informe o nome da nova categoria antes de salvar.")
            else:
                if vincular_produto and tipo_f == "Despesa":
                    if prod_fin_label == "-":
                        st.warning("Selecione o produto para vincular o custo adicional.")
                    else:
                        target_pid = int(prod_fin_label.split(" - ")[0])
                        adj_id = create_product_cost_adjustment(
                            product_id=target_pid,
                            amount=valor_f,
                            date=str(data_f),
                            note=desc_f,
                            is_paid=True
                        )
                        if adj_id:
                            st.success("Despesa vinculada ao produto e registrada como custo adicional de estoque (CMV).")
                            st.rerun()
                        else:
                            st.error("Não foi possível registrar custo adicional. Verifique se o produto tem estoque disponível.")
                    st.stop()

                # Cria a categoria se for nova
                if opcao_cat == "➕ Criar nova categoria...":
                    companies = get_companies()
                    comp_id = companies[0]['id'] if companies else 1
                    create_category(tipo_f, cat_f, comp_id)
                
                q = "INSERT INTO transactions (type, amount, category, description, date) VALUES (%s,%s,%s,%s,%s)"
                params = (tipo_f, valor_f, cat_f, desc_f, data_f)
                if run_query(q, params):
                    st.success(f"{tipo_f} lançada com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar lançamento.")


    with sub_tab3:
        st.subheader("Entrada ou Saída de Peças")
        prods_e = get_products()
        p_options_e = {p['name']: p['id'] for p in prods_e}

        stock_barcode = normalize_barcode(st.text_input(
            "Código de barras",
            key="stock_barcode_scan",
            placeholder="Escaneie para localizar ou cadastrar produto"
        ))
        stock_scan_product = find_product_by_barcode(stock_barcode) if stock_barcode else None
        if stock_scan_product:
            st.success(f"Produto localizado: {stock_scan_product['name']}")
        elif stock_barcode:
            st.info("Código novo. O cadastro rápido abaixo já vai vincular este código ao produto.")
        
        # Adiciona opção de cadastrar novo
        stock_options = ["-", "➕ Cadastrar Novo Produto"] + list(p_options_e.keys())
        default_stock_label = "➕ Cadastrar Novo Produto" if stock_barcode and not stock_scan_product else "-"
        if stock_scan_product:
            default_stock_label = next(
                (name for name, pid in p_options_e.items() if int(pid) == int(stock_scan_product["id"])),
                "-"
            )
        if default_stock_label != "-":
            st.session_state["stock_p"] = default_stock_label
        selected_p_e = st.selectbox(
            "Produto",
            options=stock_options,
            index=stock_options.index(default_stock_label) if default_stock_label in stock_options else 0,
            key="stock_p"
        )
        
        new_p_name = ""
        new_p_price = 0.0
        new_p_barcode = stock_barcode
        
        if selected_p_e == "➕ Cadastrar Novo Produto":
            col_n1, col_n2, col_n3 = st.columns(3)
            new_p_name = col_n1.text_input("Nome do Novo Produto", placeholder="Ex: Notebook i5 Dell")
            new_p_price = col_n2.number_input("Preço de Venda Sugerido (R$)", min_value=0.0, step=0.01)
            new_p_barcode = normalize_barcode(col_n3.text_input("Código", value=stock_barcode, placeholder="Código de barras"))
            st.divider()

        tipo_e = st.selectbox("Movimento", ["Entrada (Compra/Ajuste)", "Saída (Perda/Ajuste)"])
        qty_e = st.number_input("Quantidade de Itens", min_value=1, value=1, key="stock_qty")
        m_type = "in" if "Entrada" in tipo_e else "out"
        
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            consignado = st.checkbox("Produto Consignado?")
            pago = st.checkbox("Já foi pago?")
        with col_st2:
            custo_uni = st.number_input("Custo Unitário / Valor de Acerto (R$)", min_value=0.0, step=0.01, help="Mesmo se for consignado, coloque o valor que você deve pagar ao fornecedor.")

        consignment_supplier_id = None
        if consignado:
            suppliers_stock = get_consignment_suppliers()
            supplier_stock_options = {"-": None}
            supplier_stock_options.update({f"{s['name']} (ID {s['id']})": int(s['id']) for s in suppliers_stock})
            selected_stock_supplier = st.selectbox("Fornecedor consignante", options=list(supplier_stock_options.keys()), key="stock_supplier")
            consignment_supplier_id = supplier_stock_options[selected_stock_supplier]
            
        ref_e = st.text_input("Referência/Motivo", placeholder="Ex: Compra fornecedor X")

        if st.button("📦 Atualizar Estoque", use_container_width=True):
            target_p_id = None
            
            try:
                if selected_p_e == "➕ Cadastrar Novo Produto":
                    if new_p_name:
                        comps = get_companies()
                        if not comps:
                            # Se não tem empresa, cria uma padrão na hora
                            c_id = create_company("Minha Empresa")
                            if not c_id:
                                st.error("Erro fatal: Não foi possível criar uma empresa base no banco de dados.")
                                st.stop()
                        else:
                            c_id = comps[0]['id']
                        
                        target_p_id = create_product(c_id, new_p_name, new_p_price, new_p_barcode or None)
                        if not target_p_id:
                            st.error(f"Erro ao criar o produto '{new_p_name}'. Verifique o banco de dados.")
                            st.stop()
                    else:
                        st.error("Por favor, digite o nome do novo produto.")
                        st.stop()
                elif selected_p_e != "-":
                    target_p_id = p_options_e[selected_p_e]

                if target_p_id:
                    if stock_barcode and not stock_scan_product:
                        add_product_barcode(
                            product_id=target_p_id,
                            barcode=stock_barcode,
                            label="Leitura de estoque",
                            is_primary=False
                        )
                    res = add_stock_movement(
                        product_id=target_p_id,
                        quantity=qty_e,
                        movement_type=m_type,
                        reference=ref_e,
                        source="consignado" if consignado else "próprio",
                        is_paid=pago,
                        unit_cost=custo_uni,
                        consignment_supplier_id=consignment_supplier_id
                    )
                    if res:
                        st.success(f"✅ Estoque {'cadastrado e ' if selected_p_e == '➕ Cadastrar Novo Produto' else ''}atualizado!")
                        st.balloons() # Pequena comemoração visual
                    else:
                        st.error("Erro técnico ao registrar a movimentação no banco de dados.")
                else:
                    st.warning("Selecione um produto ou cadastre um novo.")
            except Exception as e:
                st.error(f"Ocorreu um erro inesperado: {e}")

    with sub_tab4:
        st.subheader("Aportes e Retiradas (Sócios)")
        partners = get_partners()
        if partners:
            p_options_s = {p['name']: p['id'] for p in partners}
            selected_p_s = st.selectbox("Sócio", options=list(p_options_s.keys()))
            tipo_s = st.radio("Ação", ["Aporte (Investimento)", "Retirada (Saque de Lucro)"], horizontal=True)
            valor_s = st.number_input("Valor R$", min_value=0.01, step=0.01, key="partner_val")
            data_s = st.date_input("Data do Evento", value=date.today(), key="partner_date")
            desc_s = st.text_input("Nota/Motivo", key="partner_note")

            if st.button("💎 Confirmar Lançamento de Sócio", use_container_width=True):
                p_id = p_options_s[selected_p_s]
                if "Aporte" in tipo_s:
                    res = create_contribution(p_id, valor_s, data_s, desc_s)
                else:
                    res = create_withdrawal(p_id, valor_s, data_s, desc_s)
                
                if res:
                    st.success("Lançamento de sócio registrado!")
                else:
                    st.error("Erro ao registrar. Verifique o saldo disponível.")
        else:
            st.warning("Nenhum sócio cadastrado. Vá em 'Gerenciar' primeiro.")

# --- TAB 2: DASHBOARD ---
with tab2:
    st.header("📊 Inteligência de Negócio")
    
    col_p, col_r = st.columns([1, 4])
    with col_p:
        period = st.selectbox("Período", ["Semana", "Mês", "Ano"], index=1)
    
    # Mapear período para o helper
    p_map = {"Semana": "week", "Mês": "month", "Ano": "year"}
    kpi_data = get_advanced_kpis(p_map[period])
    
    # Dados de Estoque e Receitas Detalhadas
    inv_data = get_inventory_report()
    rev_details = get_revenue_details()
    infra_inventory = get_infra_inventory()
    receivable_summary = get_accounts_receivable_summary()
    receivables = get_receivables_summary()
    salesperson_commissions_open = get_salesperson_commissions(open_only=True)
    salesperson_commission_balance = sum(float(item.get('outstanding_amount') or 0) for item in salesperson_commissions_open)
    consignment_payables_open = get_consignment_payables(open_only=True)
    consignment_payable_balance = sum(float(item.get('outstanding_amount') or 0) for item in consignment_payables_open)
    monthly_payables = get_monthly_payables(date.today().year, date.today().month)
    monthly_payables_pending = sum(
        float(item.get('amount') or 0)
        for item in monthly_payables
        if item.get('payment_status') == 'Pendente'
    )
    partner_capital_row = run_query("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions")
    # Mostramos o valor de VENDA total no dashboard (é o potencial de receita parada)
    total_inv_sale = sum([item.get('total_sale_value', 0) for item in inv_data]) if inv_data else 0
    total_inv_cost = sum([item.get('total_cost_value', 0) for item in inv_data]) if inv_data else 0
    total_infra_assets = sum([item.get('total_invested', 0) for item in infra_inventory]) if infra_inventory else 0
    asset_summary = get_company_assets_summary()
    company_assets = get_company_assets(active_only=True)
    total_partner_capital = float(partner_capital_row[0].get('total', 0)) if partner_capital_row else 0
    total_invested_capital = total_inv_cost + total_infra_assets

    # KPIs Principais
    if kpi_data:
        k = kpi_data[0]
        top_1, top_2, top_3, top_4, top_5 = st.columns(5)
        top_1.metric("📈 Faturamento", f"R$ {float(k.get('revenue', 0)):.2f}")
        top_2.metric("📉 Desp. Operacionais", f"R$ {float(k.get('expenses', 0)):.2f}", delta_color="inverse")
        top_3.metric("🏷️ CMV", f"R$ {float(k.get('cmv', 0)):.2f}", delta_color="inverse")
        top_4.metric("📊 Lucro Bruto", f"R$ {float(k.get('gross_profit', 0)):.2f}")
        top_5.metric("💡 Lucro Líquido", f"R$ {float(k.get('net_profit', 0)):.2f}")

        bottom_1, bottom_2, bottom_3, bottom_4 = st.columns(4)
        bottom_1.metric("🏗️ Invest. em Infra", f"R$ {float(k.get('infra_investment', 0)):.2f}", delta_color="inverse")
        bottom_2.metric("📦 Estoque (Venda)", f"R$ {total_inv_sale:.2f}")
        saldo_real = float(k.get('total_cash', 0)) + float(receivables.get('pending_total', 0) or 0)
        bottom_3.metric("💰 Saldo em Caixa", f"R$ {float(k.get('total_cash', 0)):.2f}")
        bottom_4.metric("🧾 A Prazo a Receber", f"R$ {float(receivable_summary.get('open_amount', 0)):.2f}")
    else:
        top_1, top_2, top_3, top_4, top_5 = st.columns(5)
        top_1.metric("📈 Faturamento", "R$ 0.00")
        top_2.metric("📉 Desp. Operacionais", "R$ 0.00")
        top_3.metric("🏷️ CMV", "R$ 0.00")
        top_4.metric("📊 Lucro Bruto", "R$ 0.00")
        top_5.metric("💡 Lucro Líquido", "R$ 0.00")

        bottom_1, bottom_2, bottom_3, bottom_4 = st.columns(4)
        bottom_1.metric("🏗️ Invest. em Infra", "R$ 0.00")
        bottom_2.metric("📦 Estoque (Venda)", f"R$ {total_inv_sale:.2f}")
        saldo_real = float(receivables.get('pending_total', 0) or 0)
        bottom_3.metric("💰 Saldo em Caixa", "R$ 0.00")
        bottom_4.metric("🧾 A Prazo a Receber", f"R$ {float(receivable_summary.get('open_amount', 0)):.2f}")

    extra_1, extra_2, extra_3, extra_4, extra_5 = st.columns(5)
    extra_1.metric("🤝 Aportes dos Sócios", f"R$ {total_partner_capital:.2f}")
    extra_2.metric("🏛️ Capital Investido", f"R$ {total_invested_capital:.2f}")
    extra_3.metric("🧱 Patrimônio Operacional", f"R$ {total_invested_capital + float(kpi_data[0].get('total_cash', 0)) + float(receivable_summary.get('open_amount', 0)):.2f}" if kpi_data else f"R$ {total_invested_capital + float(receivable_summary.get('open_amount', 0)):.2f}")
    extra_4.metric("👩‍💼 A repassar às vendedoras", f"R$ {salesperson_commission_balance:.2f}")
    extra_5.metric("📦 A repassar aos consignantes", f"R$ {consignment_payable_balance:.2f}")

    asset_col1, asset_col2 = st.columns(2)
    asset_col1.metric("🏢 Patrimônio cadastrado", f"R$ {float(asset_summary['total_value']):.2f}")
    asset_col2.metric("🧰 Itens patrimoniais", int(asset_summary['total_quantity']))
    with st.expander("🏢 Inventário de móveis e estrutura", expanded=False):
        if company_assets:
            asset_df = pd.DataFrame(company_assets)[[
                'name', 'category', 'quantity', 'unit_value', 'total_value',
                'location', 'condition', 'asset_code', 'note'
            ]].rename(columns={
                'name': 'Item', 'category': 'Categoria', 'quantity': 'Qtd.',
                'unit_value': 'Valor unitário', 'total_value': 'Valor total',
                'location': 'Local', 'condition': 'Estado',
                'asset_code': 'Patrimônio', 'note': 'Observação'
            })
            st.dataframe(
                asset_df.style.format({'Valor unitário': 'R$ {:.2f}', 'Valor total': 'R$ {:.2f}'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum item patrimonial cadastrado.")

    st.caption("Capital Investido = infraestrutura acumulada + estoque atual a custo. Aportes dos Sócios ficam separados porque são a origem do capital, não a aplicação dele.")
    st.caption("Saldo em Caixa não inclui vendas a prazo ainda não recebidas. O card 'A Prazo a Receber' mostra exatamente o que ainda falta entrar.")

    with st.expander(f"🗓️ Contas a pagar em {date.today().strftime('%m/%Y')} | Pendente: R$ {monthly_payables_pending:.2f}", expanded=True):
        if monthly_payables:
            payable_month_options = {
                f"Dia {int(item.get('due_day') or 0):02d} | {item['name']} | R$ {float(item['amount'] or 0):.2f} | {item['payment_status']}": item
                for item in monthly_payables
            }
            selected_month_payable_label = st.selectbox(
                "Compromisso da empresa",
                options=list(payable_month_options.keys()),
                key="monthly_payable_select"
            )
            selected_month_payable = payable_month_options[selected_month_payable_label]
            if selected_month_payable.get('payment_status') == 'Pendente':
                monthly_pay_col1, monthly_pay_col2 = st.columns(2)
                monthly_payment_amount = monthly_pay_col1.number_input(
                    "Valor pago (R$)",
                    min_value=0.01,
                    value=float(selected_month_payable['amount']),
                    step=0.01,
                    key="monthly_payment_amount"
                )
                monthly_payment_note = monthly_pay_col2.text_input("Observação", key="monthly_payment_note")
                if st.button("✅ Marcar como pago", key="mark_monthly_payable_paid"):
                    payment_id = pay_monthly_payable(
                        int(selected_month_payable['id']),
                        date.today().year,
                        date.today().month,
                        float(monthly_payment_amount),
                        date.today().isoformat(),
                        monthly_payment_note
                    )
                    if payment_id:
                        st.success("Conta marcada como paga e lançada no financeiro.")
                        st.rerun()
                    else:
                        st.error("Não foi possível marcar esta conta como paga.")
            else:
                st.success(f"Pago em {selected_month_payable.get('paid_date') or 'data não informada'}.")
            monthly_payables_df = pd.DataFrame(monthly_payables)[[
                'name', 'due_day', 'amount', 'payment_status', 'paid_amount', 'paid_date'
            ]].rename(columns={
                'name': 'Compromisso', 'due_day': 'Vencimento', 'amount': 'Valor',
                'payment_status': 'Status', 'paid_amount': 'Pago', 'paid_date': 'Data do pagamento'
            })
            st.dataframe(monthly_payables_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma conta fixa ou compromisso cadastrado para este mês.")

    with st.expander("📦 Repasses de consignação pendentes", expanded=False):
        if consignment_payables_open:
            payable_options_dashboard = {
                f"#{item['id']} | {item['supplier_name']} | {item['product_name']} | Saldo R$ {float(item['outstanding_amount']):.2f}": item
                for item in consignment_payables_open
            }
            selected_payable_label_dashboard = st.selectbox(
                "Repasse a pagar",
                options=list(payable_options_dashboard.keys()),
                key="dashboard_consignment_payable_select"
            )
            selected_payable_dashboard = payable_options_dashboard[selected_payable_label_dashboard]
            payable_outstanding_dashboard = float(selected_payable_dashboard['outstanding_amount'])
            pay_payable_col1, pay_payable_col2 = st.columns(2)
            payable_payment_amount = pay_payable_col1.number_input(
                "Valor do repasse (R$)",
                min_value=0.01,
                max_value=payable_outstanding_dashboard,
                value=payable_outstanding_dashboard,
                step=0.01,
                key="dashboard_consignment_payment_amount"
            )
            payable_payment_note = pay_payable_col2.text_input(
                "Observação do repasse",
                key="dashboard_consignment_payment_note"
            )
            if st.button("💸 Pagar repasse consignado", key="dashboard_pay_consignment"):
                payment_id = pay_consignment_payable(
                    int(selected_payable_dashboard['id']),
                    float(payable_payment_amount),
                    date.today().isoformat(),
                    payable_payment_note
                )
                if payment_id:
                    st.success("Repasse consignado pago e saldo atualizado.")
                    st.rerun()
                else:
                    st.error("Não foi possível registrar o repasse. Confira o valor informado.")
            st.dataframe(
                pd.DataFrame(consignment_payables_open)[[
                    'id', 'supplier_name', 'product_name', 'quantity', 'total_amount',
                    'paid_amount', 'outstanding_amount', 'status'
                ]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Não há valores pendentes para repassar aos consignantes.")

    with st.expander("👩‍💼 Comissões de vendedoras", expanded=False):
        if salesperson_commissions_open:
            commission_options = {
                f"#{item['id']} | {item['salesperson_name']} | {item['product_name']} | Saldo R$ {float(item['outstanding_amount']):.2f}": item
                for item in salesperson_commissions_open
            }
            selected_commission_label = st.selectbox("Comissão a pagar", options=list(commission_options.keys()), key="dashboard_commission_select")
            selected_commission = commission_options[selected_commission_label]
            commission_outstanding = float(selected_commission['outstanding_amount'])
            bonus_col1, bonus_col2 = st.columns(2)
            extra_bonus = bonus_col1.number_input(
                "Bônus extra combinado (R$)", min_value=0.0, step=0.01, value=0.0,
                key="dashboard_extra_bonus"
            )
            extra_bonus_note = bonus_col2.text_input("Motivo do bônus", key="dashboard_extra_bonus_note")
            if st.button("➕ Adicionar bônus à comissão", key="dashboard_add_bonus"):
                if extra_bonus <= 0:
                    st.warning("Informe um bônus maior que zero.")
                elif add_salesperson_bonus(int(selected_commission['id']), float(extra_bonus), extra_bonus_note):
                    st.success("Bônus adicionado. O lucro líquido e o saldo a pagar foram atualizados.")
                    st.rerun()
                else:
                    st.error("Não foi possível adicionar o bônus.")
            commission_outstanding = float(selected_commission['outstanding_amount'])
            pay_commission_col1, pay_commission_col2 = st.columns(2)
            commission_payment_amount = pay_commission_col1.number_input(
                "Valor do pagamento (R$)", min_value=0.01, max_value=commission_outstanding,
                value=commission_outstanding, step=0.01, key="dashboard_commission_amount"
            )
            commission_payment_note = pay_commission_col2.text_input("Observação", key="dashboard_commission_note")
            if st.button("💸 Pagar comissão", key="dashboard_pay_commission"):
                payment_id = pay_salesperson_commission(
                    int(selected_commission['id']),
                    float(commission_payment_amount),
                    date.today().isoformat(),
                    commission_payment_note
                )
                if payment_id:
                    st.success("Comissão paga e saldo atualizado.")
                    st.rerun()
                else:
                    st.error("Não foi possível registrar o pagamento da comissão.")
            st.dataframe(
                pd.DataFrame(salesperson_commissions_open)[[
                    'id', 'salesperson_name', 'product_name', 'sale_amount', 'cost_amount',
                    'gross_profit', 'commission_pct', 'commission_amount', 'paid_amount',
                    'net_profit',
                    'bonus_amount', 'outstanding_amount', 'status'
                ]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Não há comissões de vendedoras pendentes.")
    # Alertas
    alerts = get_upcoming_alerts()
    if alerts:
        st.warning(f"⚠️ **Atenção:** Você tem {len(alerts)} contas vencendo nos próximos 5 dias!")
        with st.expander("Ver Alertas"):
            for a in alerts:
                st.write(f"- {a['name']}: **R$ {a['amount']:.2f}** (Dia {a['due_day']})")

    st.divider()

    st.subheader("🧾 Contas a Receber")
    ar1, ar2, ar3 = st.columns(3)
    ar1.metric("Saldo em Aberto", f"R$ {float(receivable_summary.get('open_amount', 0)):.2f}")
    ar2.metric("Vencido", f"R$ {float(receivable_summary.get('overdue_amount', 0)):.2f}", delta_color="inverse")
    ar3.metric("Títulos em Aberto", int(receivable_summary.get('total_open_titles', 0)))

    receivable_items = receivable_summary.get("items", [])
    if receivable_items:
        ar_df = pd.DataFrame(receivable_items)[[
            'id', 'product_name', 'customer_name', 'sale_date', 'due_date',
            'total_amount', 'received_amount', 'outstanding_amount', 'status'
        ]].copy()
        ar_df.columns = ['ID', 'Produto', 'Cliente', 'Data Venda', 'Vencimento', 'Total', 'Recebido', 'Saldo', 'Status']
        st.dataframe(
            ar_df.style.format({
                'Total': 'R$ {:.2f}',
                'Recebido': 'R$ {:.2f}',
                'Saldo': 'R$ {:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma venda a prazo em aberto.")

    st.divider()

    # Gráficos de Receitas e Despesas
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Origem das Receitas")
        if rev_details:
            rdf = pd.DataFrame(rev_details)
            st.plotly_chart(px.pie(rdf, names='channel', values='total', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
        else:
            st.info("Sem dados de receita para detalhar.")

    with g2:
        st.subheader("Despesas por Categoria")
        rows = run_query(
            "SELECT category, SUM(amount) as total "
            "FROM transactions "
            "WHERE type='Despesa' AND COALESCE(category,'') NOT IN ('Empréstimo Sócios', 'Amortização Empréstimo', 'Estoque/Compra', 'Estoque/Custo Adicional', 'Infraestrutura', 'Software/Infra') "
            "GROUP BY category"
        )
        if rows:
            ddf = pd.DataFrame(rows)
            st.plotly_chart(px.pie(ddf, names='category', values='total', hole=0.4), use_container_width=True)
        else:
            st.info("Sem despesas registradas.")

    st.divider()

    # Estoque e Divisão de Lucros
    col_inv, col_lucro = st.columns(2)
    
    with col_inv:
        st.subheader("📦 Níveis de Estoque")
        if inv_data:
            idf = pd.DataFrame(inv_data)
            if not idf.empty:
                # Ordena colunas: id, name, price, stock_qty, last_cost, total_cost_value, total_sale_value
                idf.columns = ['ID', 'Produto', 'Preço Venda', 'Qtd', 'Últ. Custo', 'Valor (Custo)', 'Valor (Venda)']
                st.dataframe(
                    idf[['Produto', 'Qtd', 'Valor (Custo)', 'Valor (Venda)']].style.format({
                        'Valor (Custo)': 'R$ {:.2f}',
                        'Valor (Venda)': 'R$ {:.2f}'
                    }), 
                    use_container_width=True
                )
            else:
                st.info("Nenhum produto em estoque.")
        else:
            st.info("Nenhum produto em estoque.")

    with col_lucro:
        st.subheader("👥 Divisão de Lucros e Saldos")
        partner_reps = get_partner_reports()
        if isinstance(partner_reps, list) and len(partner_reps) > 0:
            pdf = pd.DataFrame(partner_reps)
            # Formatar colunas para exibição
            display_df = pdf[[
                'name', 'share_pct', 'share_of_profit',
                'pending_receivable_balance', 'available_balance',
                'total_position_balance', 'total_withdrawn'
            ]].copy()
            display_df.columns = [
                'Sócio', '% Participação', 'Lucro Gerado',
                'Saldo Pendente a Receber', 'Saldo de Lucro',
                'Saldo Total com Aportes', 'Total Retirado'
            ]
            st.table(display_df.style.format({
                '% Participação': '{:.1f}%',
                'Lucro Gerado': 'R$ {:.2f}',
                'Saldo Pendente a Receber': 'R$ {:.2f}',
                'Saldo de Lucro': 'R$ {:.2f}',
                'Saldo Total com Aportes': 'R$ {:.2f}',
                'Total Retirado': 'R$ {:.2f}',
            }))
        else:
            st.info("Cadastre sócios na aba 'Gerenciar'.")

    st.divider()

    st.subheader("🏗️ Inventário de Infraestrutura")
    if infra_inventory:
        infra_df = pd.DataFrame(infra_inventory)
        total_infra = float(infra_df['total_invested'].astype(float).sum())
        infra_items = int(len(infra_df.index))
        infra_entries = int(infra_df['entries'].astype(int).sum())

        i1, i2, i3 = st.columns(3)
        i1.metric("Itens de Infra", infra_items)
        i2.metric("Lançamentos de Infra", infra_entries)
        i3.metric("Total Investido", f"R$ {total_infra:.2f}")

        display_infra = infra_df[['item_name', 'category', 'entries', 'last_date', 'total_invested']].copy()
        display_infra.columns = ['Item', 'Categoria', 'Lançamentos', 'Última Data', 'Total Investido']
        st.dataframe(
            display_infra.style.format({
                'Total Investido': 'R$ {:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum investimento em infraestrutura encontrado até agora.")

    st.divider()
    
    # Gráficos (Mantendo os existentes com melhoria)
    g1, g2 = st.columns(2)
    rows = run_query(
        "SELECT * FROM transactions "
        "WHERE COALESCE(category,'') NOT IN ('Empréstimo Sócios', 'Amortização Empréstimo', 'Estoque/Compra', 'Estoque/Custo Adicional', 'Infraestrutura', 'Software/Infra') "
        "ORDER BY date DESC LIMIT 100"
    )
    if rows:
        df = pd.DataFrame(rows)
        df['amount'] = df['amount'].astype(float)
        with g1:
            st.subheader("Despesas por Categoria")
            despesas = df[df['type'] == 'Despesa']
            if not despesas.empty:
                despesas_agrupadas = despesas.groupby('category', dropna=False, as_index=False)['amount'].sum()
                st.plotly_chart(
                    go.Figure(data=[go.Pie(
                        labels=despesas_agrupadas['category'].fillna('Sem categoria'),
                        values=despesas_agrupadas['amount'],
                        hole=0.4
                    )]),
                    use_container_width=True
                )
        with g2:
            st.subheader("Faturamento Mensal")
            faturamento_agrupado = df.groupby(['date', 'type'], dropna=False, as_index=False)['amount'].sum()
            figura_faturamento = go.Figure()
            for tipo in faturamento_agrupado['type'].dropna().unique():
                serie = faturamento_agrupado[faturamento_agrupado['type'] == tipo]
                figura_faturamento.add_trace(go.Bar(
                    x=serie['date'],
                    y=serie['amount'],
                    name=str(tipo)
                ))
            figura_faturamento.update_layout(barmode='group')
            st.plotly_chart(figura_faturamento, use_container_width=True)

# --- TAB: ESTOQUE ---
with tab_stock:
    st.header("📦 Gestão de Estoque Detalhada")
    st.markdown("Controle o que está disponível, o que já foi vendido e os valores imobilizados.")

    stock_data = get_detailed_stock_report()
    if stock_data:
        df_stock = pd.DataFrame(stock_data)
        
        # KPIs de Estoque
        total_items = df_stock['current_stock'].sum()
        total_cost = df_stock['stock_value_cost'].sum()
        total_sale = df_stock['stock_value_sale'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Itens Disponíveis", int(total_items))
        k2.metric("Valor em Estoque (Custo)", f"R$ {total_cost:.2f}")
        k3.metric("Valor em Estoque (Venda)", f"R$ {total_sale:.2f}")

        st.divider()
        
        # Tabela Detalhada
        st.subheader("📋 Inventário Completo")
        # Mostrar Vendidos (Total Out) e Disponíveis (Current Stock)
        display_stock = df_stock[['sku', 'name', 'total_in', 'total_out', 'current_stock', 'price', 'last_cost']].copy()
        display_stock.columns = ['SKU', 'Produto', 'Entradas', 'Vendas/Saídas', 'Disponível', 'Preço Venda', 'Último Custo']
        
        st.dataframe(
            display_stock.style.format({
                'Preço Venda': 'R$ {:.2f}',
                'Último Custo': 'R$ {:.2f}'
            }), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Nenhum produto com movimentação de estoque encontrado.")

# --- TAB: HISTÓRICO ---
with tab_history:
    st.header("📜 Histórico de Lançamentos")
    st.markdown("Veja tudo o que foi lançado e cancele registros se necessário.")

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        # Padrão: 90 dias atrás para garantir que migrações apareçam
        from datetime import timedelta
        default_date = date.today() - timedelta(days=90)
        date_filter = st.date_input("Filtrar por data inicial", value=default_date)
    with col_f2:
        type_filter = st.selectbox(
            "Filtrar por tipo",
            [
                "Todos", "Receita", "Despesa", "Estoque",
                "Aporte Sócio", "Retirada Sócio",
                "Empréstimo Sócio->Empresa", "Empréstimo Empresa->Sócio", "Amortização Empréstimo",
                "Custo Adicional Produto", "Venda a Prazo", "Recebimento a Prazo"
            ]
        )
    
    # Busca dados
    all_trans = get_all_transactions(limit=300)
    if all_trans:
        df_h = pd.DataFrame(all_trans)
        df_h['date'] = pd.to_datetime(df_h['date']).dt.date
        
        # Aplicar filtros
        filtered_df = df_h[df_h['date'] >= date_filter]
        if type_filter != "Todos":
            filtered_df = filtered_df[filtered_df['type'] == type_filter]
        
        if not filtered_df.empty:
            # Seleção para deletar
            st.divider()
            st.subheader("🗑️ Cancelar um Lançamento")
            history_records = [None] + filtered_df.to_dict("records")
            to_delete = st.selectbox(
                "Escolha o lançamento para cancelar:",
                history_records,
                format_func=lambda row: (
                    "Selecione um item..."
                    if row is None
                    else f"[{row.get('source', 'transaction')}] ID: {int(row.get('source_id', row['id']))} | {row['date']} | {row['type']} | R$ {float(row['amount']):.2f} | {row['description']}"
                )
            )
            
            if to_delete is not None:
                source = to_delete.get("source", "transaction")
                source_id = int(to_delete.get("source_id", to_delete["id"]))
                if st.button("❌ Confirmar Exclusão Definitiva", type="primary"):
                    if delete_history_item(source, source_id):
                        st.success("Lançamento cancelado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir lançamento. Se for empréstimo, verifique se não há amortizações vinculadas.")

            st.divider()
            st.subheader("📋 Lista Completa")
            # Exibir tabela formatada
            display_h = filtered_df[['id', 'date', 'type', 'amount', 'category', 'description']].copy()
            display_h.columns = ['ID', 'Data', 'Tipo', 'Valor', 'Categoria', 'Descrição']
            st.dataframe(display_h.style.format({'Valor': 'R$ {:.2f}'}), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum lançamento encontrado para os filtros selecionados.")
    else:
        st.info("Ainda não há lançamentos registrados.")

# --- TAB 3: IMPORTAR ---
with tab3:
    st.header("Importação Inteligente de Planilhas")
    st.markdown("Faça upload de **Excel (.xlsx), CSV ou Texto** para identificar transações automaticamente.")

    uploaded_file = st.file_uploader("Escolha um arquivo", type=["csv", "txt", "xlsx"])
    text_input = st.text_area("Ou cole o texto do extrato aqui:")

    # Lógica de Abas do Excel
    sheet_name = None
    if uploaded_file and uploaded_file.name.endswith('.xlsx'):
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = xl.sheet_names
            if len(sheets) > 1:
                sheet_name = st.selectbox("Este arquivo tem várias abas. Escolha qual importar:", sheets)
            else:
                sheet_name = sheets[0]
        except Exception as e:
            st.error(f"Erro ao ler abas do Excel: {e}")

    if st.button("🚀 Iniciar Análise Inteligente"):
        content = ""
        if uploaded_file:
            if uploaded_file.name.endswith('.xlsx'):
                try:
                    df_xlsx = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                    content = df_xlsx.to_csv(index=False)
                except Exception as e:
                    st.error(f"Erro ao ler Excel: {e}")
            else:
                try:
                    content = uploaded_file.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    content = uploaded_file.getvalue().decode("latin-1")
        elif text_input:
            content = text_input
        
        if content:
            with st.spinner("A IA está analisando seus dados... (Pode levar alguns segundos)"):
                # Passa contexto de produtos e sócios para a IA mapear IDs automaticamente
                ctx = {
                    "products": get_products(),
                    "partners": get_partners(),
                    "companies": get_companies()
                }
                data = process_statement(content, entities_context=ctx)
                
                if isinstance(data, dict) and "error" in data:
                    st.error(data["error"])
                else:
                    # Achatar o JSON da IA para um DataFrame amigável
                    rows = []
                    for item in data:
                        intent = item.get("intent", "SAVE_TRANSACTION")
                        d = item.get("data", {})
                        
                        # Normalizar type: garante que seja sempre Receita ou Despesa
                        raw_type = d.get("type", "")
                        if isinstance(raw_type, str) and raw_type.strip() in ["Receita", "Despesa"]:
                            tipo = raw_type.strip()
                        else:
                            # Tenta inferir pelo valor: valores negativos = despesa
                            val = d.get("amount", 0)
                            tipo = "Receita" if (isinstance(val, (int, float)) and val >= 0) else "Despesa"
                        
                        rows.append({
                            "Intenção": intent,
                            "Tipo": tipo,
                            "Movimento": d.get("type") if d.get("type") in ["in", "out"] else "in",
                            "Data": d.get("date"),
                            "Valor": abs(d.get("amount", 0) or 0),
                            "Descrição": d.get("description"),
                            "Qtd": d.get("quantity", 1),
                            "Categoria": d.get("category", "Outros"),
                            "ID Produto": d.get("product_id")
                        })
                    
                    df_import = pd.DataFrame(rows)
                    if "Data" in df_import.columns:
                        df_import["Data"] = pd.to_datetime(df_import["Data"], errors='coerce').dt.date
                    
                    st.session_state.import_data = df_import
                    st.success(f"{len(df_import)} lançamentos identificados!")
        else:
            st.warning("Por favor, faça upload de um arquivo ou cole o texto.")

    # Exibição e Confirmação
    if "import_data" in st.session_state and st.session_state.import_data is not None:
        st.divider()
        st.subheader("Verifique os Lançamentos Identificados")
        
        edited_df = st.data_editor(
            st.session_state.import_data,
            num_rows="dynamic",
            column_config={
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Receita", "Despesa"], required=True),
                "Movimento": st.column_config.SelectboxColumn("Movimento", options=["in", "out"], required=True),
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD"),
                "Intenção": st.column_config.SelectboxColumn("Ação", options=["REGISTER_SALE", "STOCK_MOVEMENT", "SAVE_TRANSACTION", "PARTNER_CONTRIBUTION"]),
                "Categoria": st.column_config.TextColumn("Categoria"),
                "ID Produto": st.column_config.NumberColumn("Prod ID")
            },
            use_container_width=True
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Confirmar e Lançar Tudo"):
                success_count = 0
                error_count = 0
                
                with st.spinner("Processando lançamentos em lote..."):
                    for _, row in edited_df.iterrows():
                        intent = row['Intenção']
                        dt = row['Data']
                        val = float(row['Valor'] or 0)
                        desc = row['Descrição']
                        p_id = row['ID Produto']
                        qty = int(row['Qtd'] or 1)
                        categoria = row.get('Categoria', 'Outros')
                        movimento = row.get('Movimento', 'in')
                        if movimento not in ['in', 'out']:
                            movimento = 'in'
                        
                        # Normalização defensiva final do tipo
                        tipo_gravado = row.get('Tipo', '')
                        if tipo_gravado not in ['Receita', 'Despesa']:
                            tipo_gravado = 'Despesa'  # padrão seguro

                        try:
                            res = None
                            if intent == "REGISTER_SALE":
                                if p_id: res = create_sale(int(p_id), qty, val, description=desc, sale_date=str(dt) if dt else None)
                            elif intent == "STOCK_MOVEMENT":
                                if p_id: res = add_stock_movement(int(p_id), qty, movimento, desc, unit_cost=val/qty if qty > 0 else 0)
                            elif intent == "SAVE_TRANSACTION":
                                q = "INSERT INTO transactions (type, amount, category, description, date) VALUES (%s,%s,%s,%s,%s)"
                                params = (tipo_gravado, abs(val), categoria, desc, str(dt))
                                res = run_query(q, params)
                            elif intent == "PARTNER_CONTRIBUTION":
                                partners = get_partners()
                                if partners: res = create_contribution(partners[0]['id'], val, str(dt), desc)
                            
                            if res: success_count += 1
                            else: error_count += 1
                        except Exception as e:
                            print(f"Erro no lote (intent={intent}, data={dt}, produto={p_id}): {e}")
                            error_count += 1
                
                if success_count > 0:
                    st.success(f"Sucesso: {success_count} lançamentos realizados!")
                if error_count > 0:
                    st.error(f"Erros: {error_count} itens não puderam ser processados.")
                
                if success_count > 0:
                    st.session_state.import_data = None
                    st.balloons()
                    st.rerun()
        
        with col_b:
            if st.button("🗑️ Descartar"):
                st.session_state.import_data = None
                st.rerun()


# --- TAB 4: GERENCIAMENTO ---
with tab4:
    st.header("⚙️ Área de Gerenciamento")

    st.subheader("Empresas")
    col1, col2 = st.columns([2, 1])
    with col1:
        new_company = st.text_input("Nome da empresa", key="new_company")
    with col2:
        if st.button("➕ Criar Empresa"):
            if new_company:
                cid = create_company(new_company)
                if cid:
                    st.success(f"Empresa criada (id={cid})")
                else:
                    st.error("Erro ao criar empresa")

    companies = get_companies()
    if companies:
        st.write("Empresas cadastradas:")
        st.dataframe(pd.DataFrame(companies), use_container_width=True)

    st.divider()
    st.subheader("Fornecedores consignantes")
    supplier_company_options = {c['name']: c['id'] for c in companies} if companies else {}
    supplier_company = st.selectbox("Empresa do consignante", options=["-"] + list(supplier_company_options.keys()), key="supplier_company")
    supplier_name = st.text_input("Nome do fornecedor consignante", key="supplier_name")
    supplier_contact = st.text_input("Contato (opcional)", key="supplier_contact")
    if st.button("➕ Adicionar consignante"):
        if supplier_company == "-" or not supplier_name.strip():
            st.warning("Selecione a empresa e informe o nome do consignante.")
        else:
            supplier_id = create_consignment_supplier(supplier_company_options[supplier_company], supplier_name, supplier_contact)
            if supplier_id:
                st.success(f"Consignante criado (id={supplier_id}).")
                st.rerun()
            else:
                st.error("Não foi possível cadastrar o consignante.")

    suppliers_manage = get_consignment_suppliers()
    if suppliers_manage:
        st.dataframe(pd.DataFrame(suppliers_manage), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💸 Repasses de consignação")
    open_consignment_payables = get_consignment_payables(open_only=True)
    if open_consignment_payables:
        payable_options = {
            f"#{item['id']} | {item['supplier_name']} | {item['product_name']} | Saldo R$ {float(item['outstanding_amount']):.2f}": item
            for item in open_consignment_payables
        }
        selected_payable_label = st.selectbox("Título a pagar", options=list(payable_options.keys()), key="consignment_payable")
        selected_payable = payable_options[selected_payable_label]
        payable_outstanding = float(selected_payable['outstanding_amount'])
        pay_col1, pay_col2 = st.columns(2)
        consignment_payment_amount = pay_col1.number_input(
            "Valor do repasse (R$)", min_value=0.01, max_value=payable_outstanding,
            value=payable_outstanding, step=0.01, key="consignment_payment_amount"
        )
        consignment_payment_note = pay_col2.text_input("Observação do repasse", key="consignment_payment_note")
        if st.button("💸 Registrar repasse", use_container_width=True):
            payment_id = pay_consignment_payable(
                int(selected_payable['id']),
                float(consignment_payment_amount),
                date.today().isoformat(),
                consignment_payment_note
            )
            if payment_id:
                st.success("Repasse registrado e conta a pagar atualizada.")
                st.rerun()
            else:
                st.error("Não foi possível registrar o repasse.")
        st.dataframe(
            pd.DataFrame(open_consignment_payables)[['id', 'supplier_name', 'product_name', 'quantity', 'total_amount', 'paid_amount', 'outstanding_amount', 'status']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Não há repasses de consignação em aberto.")

    st.divider()
    st.subheader("Vendedoras e comissões")
    salesperson_company_options = {c['name']: c['id'] for c in companies} if companies else {}
    salesperson_company = st.selectbox("Empresa da vendedora", options=["-"] + list(salesperson_company_options.keys()), key="salesperson_company")
    salesperson_name = st.text_input("Nome da vendedora", key="salesperson_name")
    salesperson_contact = st.text_input("Contato da vendedora (opcional)", key="salesperson_contact")
    salesperson_default_pct = st.number_input("Percentual padrão sobre o lucro bruto (%)", min_value=0.0, max_value=100.0, step=0.1, key="salesperson_default_pct")
    if st.button("➕ Adicionar vendedora"):
        if salesperson_company == "-" or not salesperson_name.strip():
            st.warning("Selecione a empresa e informe o nome da vendedora.")
        else:
            salesperson_id_created = create_salesperson(
                salesperson_company_options[salesperson_company],
                salesperson_name,
                salesperson_contact,
                salesperson_default_pct
            )
            if salesperson_id_created:
                st.success(f"Vendedora criada (id={salesperson_id_created}).")
                st.rerun()
            else:
                st.error("Não foi possível cadastrar a vendedora.")

    salespeople_manage = get_salespeople(active_only=False)
    if salespeople_manage:
        st.dataframe(pd.DataFrame(salespeople_manage), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Sócios / Parceiros")
    st.caption("Use participação 0 para parceiros ou comissões sem direito à divisão de lucros.")
    companies_select = {c['name']: c['id'] for c in companies} if companies else {}
    comp_option = st.selectbox("Empresa", options=["-"] + list(companies_select.keys()), key="partner_company")
    pname = st.text_input("Nome do sócio / parceiro", key="partner_name")
    pshare = st.number_input("Porcentagem de participação (%)", min_value=0.0, max_value=100.0, step=0.1, key="partner_share", help="Defina 0 para comissão ou parceria sem participação nos lucros.")
    if st.button("➕ Adicionar Sócio"):
        if comp_option and comp_option != "-":
            pid = create_partner(companies_select[comp_option], pname, pshare)
            if pid:
                st.success(f"Sócio criado (id={pid})")
            else:
                st.error("Erro ao criar sócio")
        else:
            st.warning("Selecione uma empresa primeiro.")

    partners = get_partners(companies_select.get(comp_option) if comp_option != "-" else None)
    if partners:
        st.subheader("Editar Sócio / Parceiro")
        partner_select_options = {f"{p['name']} ({p['share_pct']}%)": p['id'] for p in partners}
        selected_partner_label = st.selectbox("Selecione um sócio para editar", options=["-"] + list(partner_select_options.keys()), key="edit_partner_select")
        if selected_partner_label != "-":
            selected_partner_id = partner_select_options[selected_partner_label]
            selected_partner = next((p for p in partners if p['id'] == selected_partner_id), None)
            if selected_partner:
                updated_share = st.number_input(
                    "Porcentagem de participação (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    value=float(selected_partner['share_pct']),
                    key="edit_partner_share"
                )
                if st.button("💾 Atualizar participação", key="update_partner_share"):
                    success = update_partner_share(selected_partner_id, updated_share)
                    if success:
                        st.success("Participação atualizada com sucesso.")
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar a participação.")

                if st.button("🔧 Definir participação para 70%", key="set_partner_70"):
                    success = update_partner_share(selected_partner_id, 70.0)
                    if success:
                        st.success("Participação atualizada para 70%.")
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar a participação.")

                if updated_share != 0.0 and st.button("🔁 Marcar como parceiro de comissão (0%)", key="convert_to_commission_partner"):
                    success = update_partner_share(selected_partner_id, 0.0)
                    if success:
                        st.success("Sócio convertido para parceiro de comissão.")
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar o sócio.")

        st.write("Sócios:")
        st.dataframe(pd.DataFrame(partners), use_container_width=True)

    # --- CONFIGURAÇÕES DO SISTEMA ---
    with st.expander("⚙️ Configurações do Sistema", expanded=False):
        st.subheader("Configuração da IA (Gemini)")
        # Tenta pegar a chave do .env se não houver no session_state
        current_key = st.session_state.get("api_key", os.getenv("GEMINI_API_KEY", ""))
        
        new_key = st.text_input("Gemini API Key", value=current_key, type="password", help="Obtenha sua chave em aistudio.google.com")
        
        if st.button("💾 Salvar Configurações"):
            set_api_key_permanent(new_key)
            st.success("Configurações salvas permanentemente no arquivo .env! A IA agora usará a nova chave.")

    st.divider()
    st.subheader("Produtos e Estoque")
    prod_comp = st.selectbox("Empresa para produto", options=["-"] + list(companies_select.keys()), key="prod_company")
    prod_name = st.text_input("Nome do produto", key="prod_name")
    prod_sku = st.text_input("SKU (opcional)", key="prod_sku")
    prod_price = st.number_input("Preço", min_value=0.0, format="%.2f", key="prod_price")
    if st.button("➕ Criar Produto"):
        if prod_comp and prod_comp != "-":
            normalized_sku = normalize_barcode(prod_sku)
            existing_barcode_product = find_product_by_barcode(normalized_sku) if normalized_sku else None
            if existing_barcode_product:
                st.error(f"Código já vinculado ao produto: {existing_barcode_product['name']}")
                st.stop()
            prid = create_product(companies_select[prod_comp], prod_name, prod_price, normalized_sku or None)
            if prid:
                st.success(f"Produto criado (id={prid})")
            else:
                st.error("Erro ao criar produto")
        else:
            st.warning("Selecione uma empresa para o produto.")

    prods = get_products(companies_select.get(prod_comp) if prod_comp != "-" else None)
    if prods:
        dfp = pd.DataFrame(prods)
        st.write("Produtos:")
        st.dataframe(dfp[['id','sku','name','price']], use_container_width=True)

        # Mostrar nível de estoque para produto selecionado
        selected_pid = st.selectbox("Ver estoque do produto (id)", options=["-"] + [str(p['id']) for p in prods], key="stock_pid")
        if selected_pid and selected_pid != "-":
            qty = get_stock_level(int(selected_pid))
            st.info(f"Quantidade em estoque: {qty}")

            st.markdown("**Códigos de barras do produto**")
            product_codes = get_product_barcodes(int(selected_pid))
            if product_codes:
                st.dataframe(
                    pd.DataFrame(product_codes)[['id', 'barcode', 'label', 'is_primary']],
                    use_container_width=True
                )
            else:
                st.caption("Nenhum código vinculado a este produto.")

            bc1, bc2, bc3 = st.columns([2, 2, 1])
            new_barcode = normalize_barcode(bc1.text_input("Novo código", key="new_product_barcode", placeholder="Escaneie ou digite"))
            new_barcode_label = bc2.text_input("Rótulo", key="new_product_barcode_label", placeholder="Ex: EAN, fornecedor, caixa")
            new_barcode_primary = bc3.checkbox("Principal", key="new_product_barcode_primary")

            if st.button("Vincular Código", key="btn_add_product_barcode"):
                if not new_barcode:
                    st.warning("Informe um código para vincular.")
                else:
                    found = find_product_by_barcode(new_barcode)
                    if found and int(found["id"]) != int(selected_pid):
                        st.error(f"Código já vinculado ao produto: {found['name']}")
                    else:
                        barcode_id = add_product_barcode(
                            int(selected_pid),
                            new_barcode,
                            label=new_barcode_label or None,
                            is_primary=bool(new_barcode_primary)
                        )
                        if barcode_id:
                            st.success("Código vinculado com sucesso.")
                            st.rerun()
                        else:
                            st.error("Não foi possível vincular o código.")

            if product_codes:
                remove_options = {
                    f"#{bc['id']} | {bc['barcode']} | {bc.get('label') or 'Sem rótulo'}": int(bc["id"])
                    for bc in product_codes
                }
                remove_label = st.selectbox(
                    "Remover código",
                    options=["-"] + list(remove_options.keys()),
                    key="remove_product_barcode"
                )
                if st.button("Remover Código", key="btn_remove_product_barcode"):
                    if remove_label == "-":
                        st.warning("Selecione um código para remover.")
                    elif delete_product_barcode(remove_options[remove_label]):
                        st.success("Código removido.")
                        st.rerun()
                    else:
                        st.error("Não foi possível remover o código.")

        st.markdown("**Custos Adicionais por Produto (aumenta CMV futuro)**")
        cost_product_label = st.selectbox(
            "Produto para adicionar custo",
            options=["-"] + [f"{p['id']} - {p['name']}" for p in prods],
            key="extra_cost_product"
        )
        cc1, cc2, cc3 = st.columns(3)
        extra_cost_amount = cc1.number_input("Valor do Custo (R$)", min_value=0.01, step=0.01, key="extra_cost_amount")
        extra_cost_date = cc2.date_input("Data do Custo", value=date.today(), key="extra_cost_date")
        extra_cost_note = cc3.text_input("Motivo/Nota", placeholder="Ex: reparo, componente, frete", key="extra_cost_note")

        if st.button("Adicionar Custo ao Produto", key="btn_add_product_cost"):
            if cost_product_label == "-":
                st.warning("Selecione um produto.")
            else:
                target_pid = int(cost_product_label.split(" - ")[0])
                res_adj = create_product_cost_adjustment(
                    product_id=target_pid,
                    amount=extra_cost_amount,
                    date=str(extra_cost_date),
                    note=extra_cost_note,
                    is_paid=True
                )
                if res_adj:
                    st.success(f"Custo adicional registrado (id={res_adj}). Será absorvido no CMV das próximas vendas.")
                    st.rerun()
                else:
                    st.error("Não foi possível registrar o custo. Verifique se o produto possui estoque disponível.")

    st.divider()
    st.subheader("💰 Gestão de Sócios (Aportes / Retiradas)")
    if partners:
        p_select = {p['name']: p['id'] for p in partners}
        p_opt = st.selectbox("Selecione o Sócio", options=list(p_select.keys()), key="trans_p_name")
        col_v1, col_v2 = st.columns(2)
        v_amount = col_v1.number_input("Valor (R$)", min_value=0.0, key="trans_p_val")
        v_type = col_v2.selectbox("Tipo de Operação", ["Aporte", "Retirada de Lucro"], key="trans_p_type")
        v_desc = st.text_input("Observação / Motivo", key="trans_p_desc")
        
        if st.button("Executar Lançamento de Sócio"):
            if v_type == "Aporte":
                res = create_contribution(p_select[p_opt], v_amount, date.today().isoformat(), v_desc)
            else:
                res = create_withdrawal(p_select[p_opt], v_amount, date.today().isoformat(), v_desc)
            
            if res: st.success("Operação realizada!")
            else: st.error("Erro na operação.")
    else:
        st.info("Cadastre um sócio primeiro.")

    st.divider()
    st.subheader("🏦 Empréstimos / Dívidas")
    if True:
        loan_partner_opts = {p['name']: p['id'] for p in partners}
        col_l1, col_l2, col_l3 = st.columns(3)
        creditor_sources = ["Credor externo"]
        if loan_partner_opts:
            creditor_sources.insert(0, "Sócio cadastrado")
        creditor_source = col_l1.selectbox("Origem do credor", options=creditor_sources, key="loan_creditor_source")
        if creditor_source == "Sócio cadastrado":
            loan_partner_name = col_l1.selectbox("Sócio / credor", options=list(loan_partner_opts.keys()), key="loan_partner")
            loan_partner_id = loan_partner_opts[loan_partner_name]
            loan_lender_name = loan_partner_name
            direction_options = ["Sócio -> Empresa", "Empresa -> Sócio"]
        else:
            loan_partner_name = None
            loan_partner_id = None
            loan_lender_name = col_l1.text_input("Credor", key="loan_lender_name", placeholder="Ex: Banco X, Pessoa X, agiota")
            direction_options = ["Credor -> Empresa", "Empresa -> Credor"]
        loan_direction_label = col_l2.selectbox(
            "Direção do Empréstimo",
            direction_options,
            key="loan_direction"
        )
        loan_amount = col_l3.number_input("Valor do Empréstimo (R$)", min_value=0.01, step=0.01, key="loan_amount")

        col_ld1, col_ld2, col_ld3 = st.columns(3)
        loan_date = col_ld1.date_input("Data do Empréstimo", value=date.today(), key="loan_date")
        has_due = col_ld2.checkbox("Tem vencimento?", key="loan_has_due")
        due_date = col_ld3.date_input("Data Vencimento", value=date.today(), key="loan_due_date", disabled=not has_due)

        col_li1, col_li2 = st.columns(2)
        loan_interest = col_li1.number_input("Juros (% ao mês, opcional)", min_value=0.0, step=0.1, key="loan_interest")
        loan_note = col_li2.text_input("Observação do Empréstimo", key="loan_note", placeholder="Ex: Capital de giro")

        st.markdown("**Parcelamento / juros**")
        col_lp1, col_lp2, col_lp3 = st.columns(3)
        is_installment_loan = col_lp1.checkbox("Pagar em parcelas", key="loan_is_installment")
        loan_installments = col_lp2.number_input(
            "Qtd. parcelas",
            min_value=1,
            max_value=60,
            value=5 if is_installment_loan else 1,
            step=1,
            disabled=not is_installment_loan,
            key="loan_installments"
        )
        first_installment_due = col_lp3.date_input(
            "1º vencimento",
            value=due_date if has_due else date.today(),
            disabled=not is_installment_loan,
            key="loan_first_installment_due"
        )

        calc_method = "Sem parcelas"
        installment_amount = float(loan_amount)
        total_repayable = float(loan_amount)
        if is_installment_loan:
            col_lc1, col_lc2 = st.columns([2, 1])
            calc_method = col_lc1.selectbox(
                "Como calcular as parcelas",
                ["Parcela fixa com juros ao mês (PRICE)", "Total com juros simples", "Informar valor da parcela"],
                key="loan_calc_method"
            )
            if calc_method == "Informar valor da parcela":
                installment_amount = float(col_lc2.number_input("Valor de cada parcela (R$)", min_value=0.01, step=0.01, key="loan_manual_installment_amount"))
                total_repayable = round(installment_amount * int(loan_installments), 2)
            elif calc_method == "Total com juros simples":
                monthly_rate = float(loan_interest or 0) / 100
                total_repayable = round(float(loan_amount) * (1 + monthly_rate * int(loan_installments)), 2)
                installment_amount = round(total_repayable / int(loan_installments), 2)
            else:
                monthly_rate = float(loan_interest or 0) / 100
                if monthly_rate > 0:
                    installment_amount = round(float(loan_amount) * monthly_rate / (1 - (1 + monthly_rate) ** (-int(loan_installments))), 2)
                else:
                    installment_amount = round(float(loan_amount) / int(loan_installments), 2)
                total_repayable = round(installment_amount * int(loan_installments), 2)

            preview_rows = [
                {
                    "Parcela": f"{idx}/{int(loan_installments)}",
                    "Vencimento": add_months(first_installment_due, idx - 1).isoformat(),
                    "Valor": installment_amount,
                }
                for idx in range(1, int(loan_installments) + 1)
            ]
            p1, p2, p3 = st.columns(3)
            p1.metric("Principal recebido", f"R$ {float(loan_amount):,.2f}")
            p2.metric("Total a pagar", f"R$ {total_repayable:,.2f}")
            p3.metric("Parcela", f"R$ {installment_amount:,.2f}")
            st.dataframe(pd.DataFrame(preview_rows).style.format({"Valor": "R$ {:.2f}"}), use_container_width=True, hide_index=True)

        if st.button("Registrar Empréstimo", key="btn_create_loan"):
            direction_map = {
                "Sócio -> Empresa": "partner_to_company",
                "Empresa -> Sócio": "company_to_partner",
                "Credor -> Empresa": "partner_to_company",
                "Empresa -> Credor": "company_to_partner",
            }
            if creditor_source == "Credor externo" and not str(loan_lender_name or "").strip():
                st.error("Informe o nome do credor externo.")
                loan_id = None
            else:
                loan_id = create_partner_loan(
                    partner_id=loan_partner_id,
                    lender_name=loan_lender_name,
                    direction=direction_map[loan_direction_label],
                    amount=loan_amount,
                    loan_date=str(loan_date),
                    due_date=str(due_date) if has_due else None,
                    interest_rate=loan_interest,
                    note=f"{loan_note} | {calc_method}".strip(" |"),
                    installments=int(loan_installments) if is_installment_loan else 1,
                    installment_amount=installment_amount if is_installment_loan else None,
                    first_due_date=str(first_installment_due) if is_installment_loan else None
                )
            if loan_id:
                st.success(f"Empréstimo registrado (id={loan_id}).")
                st.rerun()
            else:
                st.error("Erro ao registrar empréstimo.")

        st.markdown("**Amortização de Empréstimos**")
        open_loans = get_partner_loans(status="open")
        if open_loans:
            loan_items = {f"#{l['id']} | {l.get('lender_display') or l.get('partner_name','-')} | {'Credor->Empresa' if l['direction']=='partner_to_company' else 'Empresa->Credor'} | Saldo R$ {float(l['outstanding_amount']):.2f}": l for l in open_loans}
            selected_open_loan = st.selectbox("Selecione o empréstimo em aberto", options=list(loan_items.keys()), key="loan_payment_target")
            selected_loan = loan_items[selected_open_loan]
            pending_installments = get_partner_loan_installments(loan_id=int(selected_loan["id"]), status="open")
            selected_installment = None
            default_pay_amount = 0.01
            default_pay_date = date.today()
            if pending_installments:
                installment_items = {
                    f"Parcela {i['installment_no']}/{i['total_installments']} | Vence {i['due_date']} | Pendente R$ {float(i['amount']) - float(i.get('paid_amount') or 0):.2f}": i
                    for i in pending_installments
                }
                selected_installment_label = st.selectbox("Parcela pendente", options=list(installment_items.keys()), key="loan_payment_installment")
                selected_installment = installment_items[selected_installment_label]
                default_pay_amount = max(float(selected_installment["amount"]) - float(selected_installment.get("paid_amount") or 0), 0.01)
                default_pay_date = pd.to_datetime(selected_installment["due_date"]).date()
                st.dataframe(
                    pd.DataFrame(pending_installments)[["installment_no", "total_installments", "due_date", "amount", "paid_amount", "status"]].rename(columns={
                        "installment_no": "Parcela",
                        "total_installments": "Total",
                        "due_date": "Vencimento",
                        "amount": "Valor",
                        "paid_amount": "Pago",
                        "status": "Status",
                    }).style.format({"Valor": "R$ {:.2f}", "Pago": "R$ {:.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
            pl1, pl2, pl3 = st.columns(3)
            pay_amount = pl1.number_input("Valor da Amortização (R$)", min_value=0.01, value=float(default_pay_amount), step=0.01, key="loan_payment_amount")
            pay_date = pl2.date_input("Data da Amortização", value=default_pay_date, key="loan_payment_date")
            pay_note = pl3.text_input("Observação da Amortização", key="loan_payment_note")
            if st.button("Registrar Amortização", key="btn_add_loan_payment"):
                pay_id = add_partner_loan_payment(
                    loan_id=int(selected_loan["id"]),
                    amount=pay_amount,
                    payment_date=str(pay_date),
                    note=pay_note,
                    installment_id=int(selected_installment["id"]) if selected_installment else None
                )
                if pay_id:
                    st.success(f"Amortização registrada (id={pay_id}).")
                    st.rerun()
                else:
                    st.error("Erro ao registrar amortização. Verifique valor e saldo em aberto.")
        else:
            st.info("Não há empréstimos em aberto para amortizar.")

        summary = get_partner_loans_summary()
        if summary:
            st.markdown("**Saldos em Aberto por Sócio**")
            sum_df = pd.DataFrame(summary)
            sum_df.columns = ["ID Sócio", "Sócio", "Empresa Deve ao Sócio", "Sócio Deve à Empresa"]

            total_company_owes = float(sum_df['Empresa Deve ao Sócio'].astype(float).sum())
            total_partner_owes = float(sum_df['Sócio Deve à Empresa'].astype(float).sum())
            net_loan_balance = total_company_owes - total_partner_owes

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Empresa Deve ao Sócio", f"R$ {total_company_owes:,.2f}")
            c2.metric("Total Sócio Deve à Empresa", f"R$ {total_partner_owes:,.2f}")
            c3.metric("Balanço Líquido de Empréstimos", f"R$ {net_loan_balance:,.2f}", delta_color="normal")

            st.dataframe(
                sum_df.style.format({
                    "Empresa Deve ao Sócio": "R$ {:.2f}",
                    "Sócio Deve à Empresa": "R$ {:.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("**Ações Rápidas**")
            r1, r2 = st.columns([3, 1])
            if r1.button("Registrar novo empréstimo (sócio↔empresa)", key="quick_new_loan"):
                st.experimental_set_query_params(section="emprestimos")
                st.info("Use o formulário acima para registrar o empréstimo.")
            if r2.button("Ver relatório detalhado", key="quick_loan_report"):
                st.write("Use o painel Dashboard para análises em tempo real ou texto do histórico de empréstimos.")
        else:
            st.info("Não há registros de empréstimos ainda.")
    else:
        st.info("Cadastre um sócio para registrar empréstimos.")

    st.divider()
    st.subheader("📅 Despesas Fixas / Programadas")
    fixed_company_options = {c['name']: c['id'] for c in companies} if companies else {}
    fixed_company = st.selectbox(
        "Empresa responsável pelo compromisso",
        options=["-"] + list(fixed_company_options.keys()),
        key="fixed_expense_company"
    )
    f_name = st.text_input("Nome da Despesa (ex: Aluguel)", key="fixed_name")
    col_f1, col_f2 = st.columns(2)
    f_amount = col_f1.number_input("Valor Mensal", min_value=0.0, key="fixed_amount")
    f_day = col_f2.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10, key="fixed_day")
    
    if st.button("➕ Agendar Despesa Fixa"):
        if not companies:
            st.warning("Cadastre uma empresa primeiro na seção 'Empresas'.")
        elif not f_name.strip():
            st.warning("Informe o nome da conta, por exemplo: Aluguel, Internet ou Salários.")
        elif fixed_company == "-":
            st.warning("Selecione a empresa responsável pelo compromisso.")
        else:
            res = create_fixed_expense(fixed_company_options[fixed_company], f_name.strip(), f_amount, f_day)
            if res: st.success("Despesa fixa agendada!")
            else: st.error("Erro ao agendar.")

    st.divider()
    st.subheader("🏢 Inventário Patrimonial")
    st.caption("Cadastro de móveis, equipamentos e estrutura sem lançar receita, despesa ou alterar o caixa.")
    asset_company_options = {c['name']: c['id'] for c in companies} if companies else {}
    asset_company = st.selectbox("Empresa do patrimônio", options=["-"] + list(asset_company_options.keys()), key="asset_company")
    asset_name = st.text_input("Nome do item", placeholder="Ex: Balcão, notebook, prateleira", key="asset_name")
    asset_category = st.selectbox("Categoria", ["Móveis", "Equipamentos", "Estrutura", "Informática", "Veículos", "Outros"], key="asset_category")
    asset_col1, asset_col2, asset_col3 = st.columns(3)
    asset_quantity = asset_col1.number_input("Quantidade", min_value=1, value=1, step=1, key="asset_quantity")
    asset_unit_value = asset_col2.number_input("Valor unitário (R$)", min_value=0.0, step=0.01, key="asset_unit_value")
    asset_acquisition_date = asset_col3.date_input("Data de aquisição", value=date.today(), key="asset_acquisition_date")
    asset_col4, asset_col5, asset_col6 = st.columns(3)
    asset_location = asset_col4.text_input("Localização", placeholder="Ex: Loja, estoque, escritório", key="asset_location")
    asset_condition = asset_col5.selectbox("Estado", ["Novo", "Bom", "Usado", "Manutenção"], key="asset_condition")
    asset_code = asset_col6.text_input("Código patrimonial (opcional)", key="asset_code")
    asset_note = st.text_input("Observação", key="asset_note")
    if st.button("➕ Cadastrar item no inventário", key="create_asset"):
        if asset_company == "-":
            st.warning("Selecione a empresa do patrimônio.")
        elif not asset_name.strip():
            st.warning("Informe o nome do item.")
        else:
            asset_id = create_company_asset(
                asset_company_options[asset_company], asset_name, asset_category,
                int(asset_quantity), float(asset_unit_value), str(asset_acquisition_date),
                asset_location, asset_condition, asset_code, asset_note
            )
            if asset_id:
                st.success("Item cadastrado no inventário sem impacto no financeiro.")
                st.rerun()
            else:
                st.error("Não foi possível cadastrar o item patrimonial.")

    st.divider()
    st.subheader("💾 Backup e Restauração de Dados")
    st.info("Utilize as opções abaixo para garantir a segurança dos seus dados locais.")

    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        st.write("**Exportar Dados**")
        st.write("Baixe uma cópia completa de todos os dados do sistema em formato SQL.")
        if st.button("📤 Gerar Arquivo de Backup", use_container_width=True):
            with st.spinner("Gerando backup do banco de dados..."):
                sql_content, result = export_backup()
                if sql_content:
                    st.download_button(
                        label="📥 Baixar Backup agora",
                        data=sql_content,
                        file_name=result,
                        mime="application/sql"
                    )
                    st.success("Backup gerado com sucesso!")
                else:
                    st.error(f"Erro ao gerar backup: {result}")

    with col_b2:
        st.write("**Restaurar Dados**")
        st.write("Substitua os dados atuais enviando um arquivo de backup (.sql).")
        uploaded_backup = st.file_uploader("Selecione o arquivo .sql", type=["sql"])
        if uploaded_backup is not None:
            if st.button("⚠️ Restaurar Backup (Sobrescrever dados)", use_container_width=True):
                with st.spinner("Restaurando dados..."):
                    # Para SQLite usamos bytes, para Postgres usamos string
                    if os.getenv("DB_TYPE", "sqlite").lower() == "sqlite":
                        content = uploaded_backup.getvalue() # Bytes
                    else:
                        content = uploaded_backup.getvalue().decode("utf-8") # String
                        
                    success, message = import_backup(content)
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(f"Erro na restauração: {message}")

# --- TAB 5: EXPORTAR ---
with tab5:
    st.header("📤 Exportar Relatório Completo")
    st.write("Gere um relatório profissional com transações, lucro por produto e movimentações de sócios.")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        start_date = st.date_input("Data Início", value=date(date.today().year, date.today().month, 1), key="exp_start")
    with col_e2:
        end_date = st.date_input("Data Fim", value=date.today(), key="exp_end")

    all_time = st.checkbox("Exportar tudo (ignorar datas)", key="exp_all")
    format_opt = st.radio("Formato de exportação", ["Excel (.xlsx)", "PDF (.pdf)"], key="exp_format")

    if st.button("🚀 Gerar Relatório"):
        date_filter_sql = ""
        date_params = None
        if not all_time:
            date_filter_sql = " WHERE date BETWEEN %s AND %s"
            date_params = (str(start_date), str(end_date))

        # --- Aba 1: Transações ---
        rows_trans = run_query(
            f"SELECT date, type, amount, category, description FROM transactions{date_filter_sql} ORDER BY date DESC",
            date_params
        )
        df_trans = pd.DataFrame(rows_trans) if rows_trans else pd.DataFrame(columns=['date','type','amount','category','description'])
        df_trans.columns = ['Data','Tipo','Valor (R$)','Categoria','Descrição']

        # --- Aba 2: Lucro por Produto ---
        q_produto = f"""
        SELECT 
            p.name AS Produto,
            COUNT(m_out.id) AS Qtd_Vendida,
            ROUND(SUM(m_out.quantity * t.amount / NULLIF(
                (SELECT SUM(q2.quantity) FROM stock_movements q2 WHERE q2.product_id = p.id AND q2.movement_type='out'), 0
            )), 2) AS Receita_Total,
            ROUND(SUM(m_out.quantity * COALESCE(m_in_last.unit_cost, 0)), 2) AS CMV_Total,
            ROUND(SUM(m_out.quantity * t.amount / NULLIF(
                (SELECT SUM(q2.quantity) FROM stock_movements q2 WHERE q2.product_id = p.id AND q2.movement_type='out'), 0
            )) - SUM(m_out.quantity * COALESCE(m_in_last.unit_cost, 0)), 2) AS Lucro_Bruto
        FROM products p
        JOIN stock_movements m_out ON m_out.product_id = p.id AND m_out.movement_type='out'
        JOIN transactions t ON t.product_id = p.id AND t.type='Receita'
        LEFT JOIN (
            SELECT product_id, unit_cost FROM stock_movements
            WHERE movement_type='in' AND id IN (
                SELECT MAX(id) FROM stock_movements WHERE movement_type='in' GROUP BY product_id
            )
        ) m_in_last ON m_in_last.product_id = p.id
        GROUP BY p.id, p.name
        """
        # Abordagem mais simples e portável por produto:
        q_prod_simple = """
        SELECT 
            p.name AS Produto,
            SUM(CASE WHEN m.movement_type='out' THEN m.quantity ELSE 0 END) AS Qtd_Vendida,
            COALESCE((SELECT SUM(t2.amount) FROM transactions t2 WHERE t2.product_id=p.id AND t2.type='Receita'), 0) AS Receita_Total,
            SUM(CASE WHEN m.movement_type='out' THEN m.quantity * COALESCE(m.unit_cost,0) ELSE 0 END) AS CMV_Total,
            COALESCE((SELECT SUM(t2.amount) FROM transactions t2 WHERE t2.product_id=p.id AND t2.type='Receita'), 0) 
            - SUM(CASE WHEN m.movement_type='out' THEN m.quantity * COALESCE(m.unit_cost,0) ELSE 0 END) AS Lucro_Bruto
        FROM products p
        LEFT JOIN stock_movements m ON m.product_id = p.id
        GROUP BY p.id, p.name
        """
        rows_prod = run_query(q_prod_simple)
        df_prod = pd.DataFrame(rows_prod) if rows_prod else pd.DataFrame(columns=['Produto','Qtd_Vendida','Receita_Total','CMV_Total','Lucro_Bruto'])

        # --- Aba 3: Sócios ---
        rows_socios = run_query("""
        SELECT 
            p.name AS Socio,
            p.share_pct AS Participacao_Pct,
            COALESCE(c.total_aportado, 0) AS Total_Aportado,
            COALESCE(w.total_retirado, 0) AS Total_Retirado
        FROM partners p
        LEFT JOIN (SELECT partner_id, SUM(amount) as total_aportado FROM contributions GROUP BY partner_id) c ON c.partner_id = p.id
        LEFT JOIN (SELECT partner_id, SUM(amount) as total_retirado FROM withdrawals GROUP BY partner_id) w ON w.partner_id = p.id
        """)
        df_socios_base = pd.DataFrame(rows_socios) if rows_socios else pd.DataFrame()

        # Detalhes de aportes e retiradas
        rows_aportes = run_query("""
        SELECT p.name AS Socio, 'Aporte' AS Tipo, c.amount AS Valor, c.date AS Data, c.note AS Nota
        FROM contributions c JOIN partners p ON c.partner_id = p.id
        UNION ALL
        SELECT p.name AS Socio, 'Retirada' AS Tipo, w.amount AS Valor, w.date AS Data, w.reason AS Nota
        FROM withdrawals w JOIN partners p ON w.partner_id = p.id
        ORDER BY Data DESC
        """)
        df_mov_socios = pd.DataFrame(rows_aportes) if rows_aportes else pd.DataFrame(columns=['Socio','Tipo','Valor','Data','Nota'])

        if format_opt == "Excel (.xlsx)":
            try:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Aba de Resumo
                    kpi_data_exp = get_advanced_kpis('year')
                    if kpi_data_exp:
                        k = kpi_data_exp[0]
                        df_resumo = pd.DataFrame([{
                            'Faturamento (R$)': round(float(k.get('revenue',0)),2),
                            'Despesas (R$)': round(float(k.get('expenses',0)),2),
                            'CMV (R$)': round(float(k.get('cmv',0)),2),
                            'Lucro Liquido (R$)': round(float(k.get('net_profit',0)),2),
                            'Saldo em Caixa (R$)': round(float(k.get('total_cash',0)),2),
                        }])
                        df_resumo.to_excel(writer, index=False, sheet_name='Resumo')
                    df_trans.to_excel(writer, index=False, sheet_name='Transacoes')
                    df_prod.to_excel(writer, index=False, sheet_name='Lucro por Produto')
                    if not df_socios_base.empty:
                        df_socios_base.to_excel(writer, index=False, sheet_name='Socios - Resumo')
                    if not df_mov_socios.empty:
                        df_mov_socios.to_excel(writer, index=False, sheet_name='Socios - Movimentacoes')

                processed_data = output.getvalue()
                st.download_button(
                    label="📥 Baixar Relatório Excel Completo",
                    data=processed_data,
                    file_name=f"relatorio_completo_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ Relatório Excel gerado com 5 abas: Resumo, Transações, Lucro por Produto, Sócios Resumo, Sócios Movimentações")
            except Exception as e:
                st.error(f"Erro ao gerar Excel: {e}")

        else:  # PDF
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)

                def pdf_section_header(title):
                    pdf.add_page()
                    pdf.set_font("Helvetica", 'B', 14)
                    pdf.set_fill_color(40, 40, 40)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 10, title, ln=True, fill=True, align='C')
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(4)

                def pdf_table(df, col_widths):
                    pdf.set_font("Helvetica", 'B', 8)
                    pdf.set_fill_color(220, 220, 220)
                    for col, w in zip(df.columns, col_widths):
                        pdf.cell(w, 7, str(col)[:20], 1, 0, 'C', True)
                    pdf.ln()
                    pdf.set_font("Helvetica", size=8)
                    for _, row in df.iterrows():
                        for val, w in zip(row.values, col_widths):
                            txt = f"R$ {float(val):.2f}" if isinstance(val, (int, float)) else str(val)[:22]
                            pdf.cell(w, 6, txt, 1)
                        pdf.ln()

                # Capa
                pdf.add_page()
                pdf.set_font("Helvetica", 'B', 20)
                pdf.ln(30)
                pdf.cell(0, 10, "Relatorio Financeiro Completo", ln=True, align='C')
                pdf.set_font("Helvetica", size=12)
                pdf.cell(0, 8, f"Gerado em: {date.today()}", ln=True, align='C')
                if not all_time:
                    pdf.cell(0, 8, f"Periodo: {start_date} a {end_date}", ln=True, align='C')

                # Resumo KPIs
                kpi_data_exp = get_advanced_kpis('year')
                if kpi_data_exp:
                    k = kpi_data_exp[0]
                    pdf_section_header("RESUMO FINANCEIRO (ANO ATUAL)")
                    pdf.set_font("Helvetica", size=11)
                    kpis = [
                        ("Faturamento Total", k.get('revenue', 0)),
                        ("Despesas Totais", k.get('expenses', 0)),
                        ("CMV (Custo Mercadorias)", k.get('cmv', 0)),
                        ("Lucro Liquido", k.get('net_profit', 0)),
                        ("Saldo em Caixa", k.get('total_cash', 0)),
                    ]
                    for label, val in kpis:
                        pdf.cell(100, 8, label + ":", 0)
                        pdf.cell(50, 8, f"R$ {float(val):.2f}", 0, ln=True)

                # Transações
                if not df_trans.empty:
                    pdf_section_header("TRANSACOES")
                    pdf_table(df_trans, [25, 18, 25, 35, 87])

                # Lucro por produto
                if not df_prod.empty:
                    pdf_section_header("LUCRO POR PRODUTO")
                    pdf_table(df_prod, [55, 20, 32, 32, 32])

                # Movimentações de sócios
                if not df_mov_socios.empty:
                    pdf_section_header("MOVIMENTACOES DE SOCIOS (Aportes e Retiradas)")
                    pdf_table(df_mov_socios, [40, 22, 28, 25, 75])

                pdf_bytes = bytes(pdf.output())
                st.download_button(
                    label="📥 Baixar Relatório PDF Completo",
                    data=pdf_bytes,
                    file_name=f"relatorio_completo_{date.today()}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ PDF completo gerado com todas as seções!")
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")
