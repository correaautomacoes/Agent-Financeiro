import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import io
from database import run_query, save_transactions_batch
from ai_agent import process_chat_command, generate_ai_reply, process_statement
from db_helpers import (
    create_company, get_companies,
    create_partner, get_partners,
    create_product, get_products,
    add_stock_movement, get_stock_level,
    get_expense_types, get_income_types,
    create_sale, create_contribution, create_withdrawal,
    get_partner_reports, get_advanced_kpis, get_upcoming_alerts,
    create_fixed_expense, get_inventory_report, get_revenue_details
)
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# ... (sidebar debug code) ...

st.set_page_config(page_title="Agente Financeiro", page_icon="💰", layout="wide")

st.title("💰 Agente Financeiro Inteligente")

# Abas para separar Chat, Dashboard e Importação
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📊 Dashboard", "📂 Importar", "⚙️ Gerenciar", "📤 Exportar"])

# --- TAB 1: CHAT ---
with tab1:
    col_chat, col_info = st.columns([2, 1])
    
    with col_info:
        st.subheader("🛠️ O que deseja fazer?")
        intent_options = {
            "💰 Lançar Receita/Despesa": "SAVE_TRANSACTION",
            "🛒 Registrar Venda": "REGISTER_SALE",
            "📦 Movimentação de Estoque": "STOCK_MOVEMENT",
            "🤝 Lançamento de Sócio": "PARTNER_CONTRIBUTION",
            "💸 Retirada de Sócio": "PARTNER_WITHDRAWAL",
            "📝 Criar Produto": "CREATE_PRODUCT"
        }
        selected_label = st.radio("Escolha uma ação para guiar a IA:", options=list(intent_options.keys()))
        selected_intent = intent_options[selected_label]
        
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
                    if intent == "SAVE_TRANSACTION":
                        q = "INSERT INTO transactions (type, amount, category, description, date) VALUES (%s,%s,%s,%s,%s)"
                        params = (data.get("type"), data.get("amount"), data.get("category"), data.get("description"), data.get("date"))
                        success = run_query(q, params)
                    
                    elif intent == "REGISTER_SALE":
                        # Usa o helper de venda que já baixa estoque
                        res = create_sale(
                            product_id=data.get("product_id"),
                            quantity=data.get("quantity", 1),
                            unit_price=data.get("amount", 0) / data.get("quantity", 1),
                            description=data.get("description")
                        )
                        success = res is not None
                    
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
                        # Identifica tipo de movimento da IA ou assume 'in' se for compra/chegada
                        m_type = data.get("type", "in")
                        qty = int(data.get("quantity", 1))
                        p_id = data.get("product_id")
                        
                        if p_id:
                            res = add_stock_movement(
                                product_id=int(p_id),
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
    total_inv_value = sum([item['total_value'] for item in inv_data]) if inv_data else 0

    if kpi_data:
        k = kpi_data[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {k['revenue']:.2f}")
        c2.metric("Despesas", f"R$ {k['expenses']:.2f}", delta_color="inverse")
        c3.metric("Lucro Líquido", f"R$ {k['net_profit']:.2f}")
        c4.metric("Valor em Estoque", f"R$ {total_inv_value:.2f}")

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
                idf.columns = ['ID', 'Produto', 'Preço Unit.', 'Quantidade', 'Valor Total']
                st.dataframe(idf[['Produto', 'Quantidade', 'Valor Total']].style.format({'Valor Total': 'R$ {:.2f}'}), use_container_width=True)
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

# --- TAB 3: IMPORTAR ---
with tab3:
    st.header("Importação de Extratos")
    st.markdown("Faça upload de **CSV, TXT ou copie o texto** do seu extrato para identificar transações automaticamente.")

    uploaded_file = st.file_uploader("Escolha um arquivo", type=["csv", "txt"])
    text_input = st.text_area("Ou cole o texto do extrato aqui:")

    if st.button("🚀 Processar Arquivo/Texto"):
        content = ""
        if uploaded_file:
            # Tenta ler como utf-8, se falhar, tenta latin-1
            try:
                content = uploaded_file.getvalue().decode("utf-8")
            except:
                content = uploaded_file.getvalue().decode("latin-1")
        elif text_input:
            content = text_input
        
        if content:
            with st.spinner("A IA está lendo seu extrato e categorizando... (Isso pode levar alguns segundos)"):
                data = process_statement(content)
                
                if "error" in data:
                    st.error(data["error"])
                else:
                    # Converter para DataFrame para edição
                    df_import = pd.DataFrame(data)
                    # Converter coluna de data para datetime para o editor funcionar
                    if "date" in df_import.columns:
                        df_import["date"] = pd.to_datetime(df_import["date"]).dt.date
                    
                    st.session_state.import_data = df_import
                    st.success(f"{len(df_import)} transações encontradas!")
        else:
            st.warning("Por favor, faça upload de um arquivo ou cole o texto.")

    # Se houver dados importados na sessão, mostra editor
    if "import_data" in st.session_state and st.session_state.import_data is not None:
        st.divider()
        st.subheader("Verifique e Corrija")
        
        # Editor de dados (Excel-like)
        edited_df = st.data_editor(
            st.session_state.import_data,
            num_rows="dynamic",
            column_config={
                "amount": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "date": st.column_config.DateColumn("Data", format="YYYY-MM-DD"),
                "type": st.column_config.SelectboxColumn("Tipo", options=["Receita", "Despesa"]),
                "category": st.column_config.SelectboxColumn("Categoria", options=[
                    "Alimentação", "Transporte", "Casa", "Lazer", "Outros", "Salário", "Investimento"
                ])
            },
            use_container_width=True
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Salvar Tudo no Banco"):
                if save_transactions_batch(edited_df):
                    st.success("Tudo salvo com sucesso!")
                    st.session_state.import_data = None # Limpa após salvar
                    st.balloons()
                else:
                    st.error("Erro ao salvar no banco de dados.")
        
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

# --- TAB 5: EXPORTAR ---
with tab5:
    st.header("📤 Exportar Dados")
    st.write("Escolha o período e o formato para exportar as transações.")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        start_date = st.date_input("Data Início", value=date(date.today().year, date.today().month, 1), key="exp_start")
    with col_e2:
        end_date = st.date_input("Data Fim", value=date.today(), key="exp_end")

    all_time = st.checkbox("Exportar tudo (ignorar datas)", key="exp_all")

    format_opt = st.radio("Formato de exportação", ["Excel (.xlsx)", "PDF (.pdf)"], key="exp_format")

    if st.button("🚀 Gerar Arquivo para Exportação"):
        query = "SELECT * FROM transactions"
        params = ()
        if not all_time:
            query += " WHERE date BETWEEN %s AND %s"
            params = (start_date, end_date)
        query += " ORDER BY date DESC"

        rows = run_query(query, params)
        if not rows:
            st.warning("Nenhum dado encontrado no período selecionado.")
        else:
            df_export = pd.DataFrame(rows)
            # Reordenar colunas amigavelmente
            cols_order = ['date', 'type', 'amount', 'category', 'description']
            existing_cols = [c for c in cols_order if c in df_export.columns]
            df_export = df_export[existing_cols]

            if format_opt == "Excel (.xlsx)":
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Transacoes')
                    processed_data = output.getvalue()
                    st.download_button(
                        label="📥 Clique aqui para baixar o Excel",
                        data=processed_data,
                        file_name=f"export_erpj_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Arquivo Excel gerado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao gerar Excel: {e}")

            else: # PDF
                try:
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", 'B', 16)
                    pdf.cell(0, 10, "Relatorio de Transacoes - ERP Inteligente", ln=True, align='C')
                    pdf.set_font("Helvetica", size=10)
                    pdf.ln(10)
                    
                    # Header
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(25, 10, "Data", 1, 0, 'C', True)
                    pdf.cell(20, 10, "Tipo", 1, 0, 'C', True)
                    pdf.cell(30, 10, "Valor", 1, 0, 'C', True)
                    pdf.cell(40, 10, "Categoria", 1, 0, 'C', True)
                    pdf.cell(75, 10, "Descricao", 1, 1, 'C', True)
                    
                    # Rows
                    for _, row in df_export.iterrows():
                        pdf.cell(25, 8, str(row.get('date', '')), 1)
                        pdf.cell(20, 8, str(row.get('type', '')), 1)
                        amt = float(row.get('amount', 0))
                        pdf.cell(30, 8, f"R$ {amt:.2f}", 1) 
                        cat = str(row.get('category', ''))
                        pdf.cell(40, 8, cat[:20], 1)
                        desc = str(row.get('description', ''))
                        pdf.cell(75, 8, desc[:40], 1, 1)
                    
                    # Para fpdf2, .output() sem argumentos retorna um bytearray
                    pdf_bytes = bytes(pdf.output())
                    st.download_button(
                        label="📥 Clique aqui para baixar o PDF",
                        data=pdf_bytes,
                        file_name=f"export_erpj_{date.today()}.pdf",
                        mime="application/pdf"
                    )
                    st.success("Arquivo PDF gerado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

