import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import io
from database import run_query, save_transactions_batch
from ai_agent import process_chat_command, generate_ai_reply, process_statement, set_api_key_permanent
from db_helpers import (
    create_company, get_companies,
    create_partner, get_partners,
    create_product, get_products,
    add_stock_movement, get_stock_level,
    get_expense_types, get_income_types,
    create_sale, create_contribution, create_withdrawal,
    get_partner_reports, get_advanced_kpis, get_upcoming_alerts,
    create_fixed_expense, get_inventory_report, get_revenue_details,
    delete_transaction, get_all_transactions, get_detailed_stock_report,
    get_categories, create_category
)
from backup_utils import export_backup, import_backup
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# ... (sidebar debug code) ...

st.set_page_config(page_title="Agente Financeiro", page_icon="💰", layout="wide")

st.title("💰 Agente Financeiro Inteligente")

# Abas para separar Chat, Lançamentos, Dashboard, Histórico, Importação e Gerenciamento
tab1, tab_manual, tab2, tab_stock, tab_history, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📝 Lançamentos", "📊 Dashboard", "📦 Estoque", "📜 Histórico", "📂 Importar", "⚙️ Gerenciar", "📤 Exportar"])

# --- TAB 1: CHAT ---
with tab1:
    col_chat, col_info = st.columns([2, 1])
    
    with col_info:
        st.subheader("🛠️ O que deseja fazer?")
        intent_option = st.radio("Escolha uma ação para guiar a IA:", 
                                ["Lançar Receita/Despesa", "Registrar Venda", "Entrada/Saída de Estoque", "Lançamento de Sócio", "Retirada de Sócio", "Criar Produto"])
        
        intent_map = {
            "Lançar Receita/Despesa": "SAVE_TRANSACTION",
            "Registrar Venda": "REGISTER_SALE",
            "Entrada/Saída de Estoque": "STOCK_MOVEMENT",
            "Lançamento de Sócio": "PARTNER_CONTRIBUTION",
            "Retirada de Sócio": "PARTNER_WITHDRAWAL",
            "Criar Produto": "CREATE_PRODUCT"
        }
        selected_label = intent_option
        selected_intent = intent_map[selected_label]
        
        # Dicas dinâmicas
        hints = {
            "SAVE_TRANSACTION": "Ex: 'Paguei 50 reais de energia' ou 'Recebi 100 de um frete'",
            "REGISTER_SALE": "Ex: 'Vendi 2 unidades do Produto X'",
            "STOCK_MOVEMENT": "Ex: 'Chegaram 10 unidades do Produto Y no estoque'",
            "PARTNER_CONTRIBUTION": "Ex: 'Sócio João fez um aporte de 1000 reais'",
            "PARTNER_WITHDRAWAL": "Ex: 'Sócio Maria retirou 500 reais de lucro'",
            "CREATE_PRODUCT": "Ex: 'Criar produto Pizza de Calabresa por 45 reais'"
        }
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
                    # Coletar entidades para a IA mapear IDs
                    entities = {
                        "produtos": get_products(),
                        "socios": get_partners()
                    }
                    
                    # Envia o prompt atual + dados que já temos (contexto) + intenção sugerida
                    context = st.session_state.current_action.get("data") if st.session_state.current_action else None
                    ai_res = process_chat_command(prompt, context, selected_intent, entities)
                    
                    if "error" in ai_res:
                        st.error(ai_res["error"])
                    else:
                        st.session_state.current_action = ai_res
                        reply = generate_ai_reply(ai_res)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.markdown(reply)

    # Área de confirmação (só aparece quando a IA diz que está COMPLETE)
    if st.session_state.current_action and st.session_state.current_action.get("status") == "COMPLETE":
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
                            # Usa o helper de venda que já baixa estoque
                            res = create_sale(
                                product_id=p_id,
                                quantity=data.get("quantity", 1),
                                unit_price=data.get("amount", 0) / data.get("quantity", 1) if data.get("quantity", 1) > 0 else 0,
                                description=data.get("description")
                            )
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
                                unit_cost=data.get("amount", 0)
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
                                unit_cost=float(data.get("amount", 0)) / qty if qty > 0 else 0
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
            p_options = {f"{p['name']} (Padrão: R$ {float(p['price']):.2f})": p['id'] for p in prods}
            selected_p = st.selectbox("Selecione o Produto", options=["-"] + list(p_options.keys()))
            
            if selected_p != "-":
                p_id = p_options[selected_p]
                p_obj = prods_dict[p_id]
                
                col_v1, col_v2 = st.columns(2)
                qty_venda = col_v1.number_input("Quantidade", min_value=1, value=1, key="v_qty")
                preco_venda = col_v2.number_input(
                    "Preço Unit. de Venda (R$)",
                    min_value=0.01, step=0.01,
                    value=float(p_obj['price']),
                    help="Pode alterar o preço para esta venda específica."
                )
                
                # Preview do lucro
                ultimo_custo_res = run_query(
                    "SELECT unit_cost FROM stock_movements WHERE product_id = %s AND movement_type='in' AND unit_cost > 0 ORDER BY id DESC LIMIT 1",
                    (p_id,)
                )
                ultimo_custo = float(ultimo_custo_res[0]['unit_cost']) if ultimo_custo_res else 0.0
                total_venda = preco_venda * qty_venda
                lucro_bruto = (preco_venda - ultimo_custo) * qty_venda
                
                col_i1, col_i2 = st.columns(2)
                col_i1.info(f"💰 **Total da Venda:** R$ {total_venda:.2f}")
                if ultimo_custo > 0:
                    col_i2.success(f"📈 **Lucro desta venda:** R$ {lucro_bruto:.2f}")
                
                desc_venda = st.text_input("Observação (opcional)", placeholder="Ex: Venda balcão")
                
                if st.button("🚀 Registrar Venda", use_container_width=True):
                    res = create_sale(p_id, qty_venda, preco_venda, desc_venda)
                    if res:
                        st.success(f"✅ Venda de R$ {total_venda:.2f} registrada!")
                        st.rerun()
                    else:
                        st.error("Erro ao registrar venda. Verifique o estoque disponível.")

    with sub_tab2:
        st.subheader("Nova Receita ou Despesa")
        tipo_f = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
        valor_f = st.number_input("Valor (R$)", min_value=0.01, step=0.01)
        
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
        
        # Adiciona opção de cadastrar novo
        selected_p_e = st.selectbox("Produto", options=["-", "➕ Cadastrar Novo Produto"] + list(p_options_e.keys()), key="stock_p")
        
        new_p_name = ""
        new_p_price = 0.0
        
        if selected_p_e == "➕ Cadastrar Novo Produto":
            col_n1, col_n2 = st.columns(2)
            new_p_name = col_n1.text_input("Nome do Novo Produto", placeholder="Ex: Notebook i5 Dell")
            new_p_price = col_n2.number_input("Preço de Venda Sugerido (R$)", min_value=0.0, step=0.01)
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
                        
                        target_p_id = create_product(c_id, new_p_name, new_p_price)
                        if not target_p_id:
                            st.error(f"Erro ao criar o produto '{new_p_name}'. Verifique o banco de dados.")
                            st.stop()
                    else:
                        st.error("Por favor, digite o nome do novo produto.")
                        st.stop()
                elif selected_p_e != "-":
                    target_p_id = p_options_e[selected_p_e]

                if target_p_id:
                    res = add_stock_movement(
                        product_id=target_p_id,
                        quantity=qty_e,
                        movement_type=m_type,
                        reference=ref_e,
                        source="consignado" if consignado else "próprio",
                        is_paid=pago,
                        unit_cost=custo_uni
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
    # Mostramos o valor de VENDA total no dashboard (é o potencial de receita parada)
    total_inv_sale = sum([item.get('total_sale_value', 0) for item in inv_data]) if inv_data else 0

    # KPIs Principais
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    if kpi_data:
        k = kpi_data[0]
        c1.metric("📈 Faturamento", f"R$ {float(k.get('revenue', 0)):.2f}")
        c2.metric("📉 Despesas", f"R$ {float(k.get('expenses', 0)):.2f}", delta_color="inverse")
        c3.metric("🏷️ CMV (Custo Vendas)", f"R$ {float(k.get('cmv', 0)):.2f}", delta_color="inverse")
        c4.metric("💡 Lucro Líquido", f"R$ {float(k.get('net_profit', 0)):.2f}")
        c5.metric("📦 Estoque (Venda)", f"R$ {total_inv_sale:.2f}")
        c6.metric("💰 Saldo em Caixa", f"R$ {float(k.get('total_cash', 0)):.2f}")
    else:
        c1.metric("📈 Faturamento", "R$ 0.00")
        c2.metric("📉 Despesas", "R$ 0.00")
        c3.metric("🏷️ CMV (Custo Vendas)", "R$ 0.00")
        c4.metric("💡 Lucro Líquido", "R$ 0.00")
        c5.metric("📦 Estoque (Venda)", f"R$ {total_inv_sale:.2f}")
        c6.metric("💰 Saldo em Caixa", "R$ 0.00")

    # Alertas
    alerts = get_upcoming_alerts()
    if alerts:
        st.warning(f"⚠️ **Atenção:** Você tem {len(alerts)} contas vencendo nos próximos 5 dias!")
        with st.expander("Ver Alertas"):
            for a in alerts:
                st.write(f"- {a['name']}: **R$ {a['amount']:.2f}** (Dia {a['due_day']})")

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
        rows = run_query("SELECT category, SUM(amount) as total FROM transactions WHERE type='Despesa' GROUP BY category")
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
            display_df = pdf[['name', 'share_pct', 'share_of_profit', 'total_withdrawn', 'current_balance']].copy()
            display_df.columns = ['Sócio', '% Participação', 'Lucro Gerado', 'Total Retirado', 'Saldo Disponível']
            st.table(display_df.style.format({
                '% Participação': '{:.1f}%',
                'Lucro Gerado': 'R$ {:.2f}',
                'Total Retirado': 'R$ {:.2f}',
                'Saldo Disponível': 'R$ {:.2f}'
            }))
        else:
            st.info("Cadastre sócios na aba 'Gerenciar'.")

    st.divider()
    
    # Gráficos (Mantendo os existentes com melhoria)
    g1, g2 = st.columns(2)
    rows = run_query("SELECT * FROM transactions ORDER BY date DESC LIMIT 100")
    if rows:
        df = pd.DataFrame(rows)
        df['amount'] = df['amount'].astype(float)
        with g1:
            st.subheader("Despesas por Categoria")
            despesas = df[df['type'] == 'Despesa']
            if not despesas.empty:
                st.plotly_chart(px.pie(despesas, names='category', values='amount', hole=0.4), use_container_width=True)
        with g2:
            st.subheader("Faturamento Mensal")
            st.plotly_chart(px.bar(df, x='date', y='amount', color='type', barmode='group'), use_container_width=True)

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
        type_filter = st.selectbox("Filtrar por tipo", ["Todos", "Receita", "Despesa"])
    
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
            options = ["Selecione um item..."] + [f"ID: {row['id']} | {row['date']} | {row['type']} | R$ {row['amount']:.2f} | {row['description']}" for _, row in filtered_df.iterrows()]
            to_delete = st.selectbox("Escolha o lançamento para cancelar:", options)
            
            if to_delete != "Selecione um item...":
                t_id = int(to_delete.split("|")[0].replace("ID: ", "").strip())
                if st.button("❌ Confirmar Exclusão Definitiva", type="primary"):
                    if delete_transaction(t_id):
                        st.success("Lançamento cancelado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir lançamento.")

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
                except:
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
                        
                        # Normalização defensiva final do tipo
                        tipo_gravado = row.get('Tipo', '')
                        if tipo_gravado not in ['Receita', 'Despesa']:
                            tipo_gravado = 'Despesa'  # padrão seguro

                        try:
                            res = None
                            if intent == "REGISTER_SALE":
                                if p_id: res = create_sale(int(p_id), qty, val, desc)
                            elif intent == "STOCK_MOVEMENT":
                                if p_id: res = add_stock_movement(int(p_id), qty, 'in', desc, unit_cost=val/qty if qty > 0 else 0)
                            elif intent == "SAVE_TRANSACTION":
                                q = "INSERT INTO transactions (type, amount, category, description, date) VALUES (%s,%s,%s,%s,%s)"
                                params = (tipo_gravado, abs(val), categoria, desc, str(dt))
                                res = run_query(q, params)
                            elif intent == "PARTNER_CONTRIBUTION":
                                partners = get_partners()
                                if partners: res = create_contribution(partners[0]['id'], val, str(dt), desc)
                            
                            if res: success_count += 1
                            else: error_count += 1
                        except:
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
    st.subheader("Sócios / Parceiros")
    companies_select = {c['name']: c['id'] for c in companies} if companies else {}
    comp_option = st.selectbox("Empresa", options=["-"] + list(companies_select.keys()), key="partner_company")
    pname = st.text_input("Nome do sócio", key="partner_name")
    pshare = st.number_input("Porcentagem de participação (%)", min_value=0.0, max_value=100.0, step=0.1, key="partner_share")
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
            prid = create_product(companies_select[prod_comp], prod_name, prod_price, prod_sku)
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
    st.subheader("📅 Despesas Fixas / Programadas")
    f_name = st.text_input("Nome da Despesa (ex: Aluguel)", key="fixed_name")
    col_f1, col_f2 = st.columns(2)
    f_amount = col_f1.number_input("Valor Mensal", min_value=0.0, key="fixed_amount")
    f_day = col_f2.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10, key="fixed_day")
    
    if st.button("➕ Agendar Despesa Fixa"):
        if f_name and comp_option != "-":
            res = create_fixed_expense(companies_select[comp_option], f_name, f_amount, f_day)
            if res: st.success("Despesa fixa agendada!")
            else: st.error("Erro ao agendar.")
        else:
            st.warning("Preencha o nome e selecione a empresa.")

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
                    if os.getenv("DB_TYPE", "postgres").lower() == "sqlite":
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
        date_filter_sql = "" if all_time else f" WHERE date BETWEEN '{start_date}' AND '{end_date}'"
        date_filter_sql_t = "" if all_time else f" WHERE t.date BETWEEN '{start_date}' AND '{end_date}'"

        # --- Aba 1: Transações ---
        rows_trans = run_query(f"SELECT date, type, amount, category, description FROM transactions{date_filter_sql} ORDER BY date DESC")
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

