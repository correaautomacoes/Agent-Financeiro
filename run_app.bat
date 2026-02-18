@echo off
echo Iniciando Agente Financeiro...
echo Certifique-se que o Docker esta rodando (para o Banco de Dados)
echo.
echo [1/1] Iniciando Interface (Streamlit)...
streamlit run app.py
pause
