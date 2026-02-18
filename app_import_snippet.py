
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
