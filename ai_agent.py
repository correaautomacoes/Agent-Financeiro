import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import date, datetime
from decimal import Decimal

# Função robusta para limpar Decimais e Datas antes do JSON
def sanitize_data(data):
    if isinstance(data, list):
        return [sanitize_data(v) for v in data]
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    return data

load_dotenv()

# Prioriza a chave vinda da interface (session_state), depois .env
def get_api_key():
    try:
        import streamlit as st
        if "api_key" in st.session_state and st.session_state.api_key:
            return st.session_state.api_key
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")

def set_api_key_permanent(new_key):
    """Grava a nova chave permanentemente no arquivo .env"""
    env_path = ".env"
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={new_key}\n")
    else:
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        with open(env_path, "w") as f:
            found = False
            for line in lines:
                if line.startswith("GEMINI_API_KEY="):
                    f.write(f"GEMINI_API_KEY={new_key}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"GEMINI_API_KEY={new_key}\n")
    
    # Atualiza o ambiente do processo atual também
    os.environ["GEMINI_API_KEY"] = new_key
    try:
        import streamlit as st
        st.session_state.api_key = new_key
    except Exception:
        pass

def configure_genai():
    key = get_api_key()
    if key:
        genai.configure(api_key=key)
        return True
    return False

# Tentando usar o modelo mais leve "latest"
MODEL_NAME = "gemini-flash-latest"

def process_chat_command(user_input, context_data=None, suggested_intent=None, entities=None):
    """
    Usa o Gemini somente para responder perguntas analíticas sobre os dados.
    Este fluxo é somente leitura e nunca retorna uma operação de gravação.
    """
    if not configure_genai():
        return {"error": "API Key não configurada. Vá em 'Gerenciar' e configure sua chave."}

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        today = date.today().isoformat()
        
        data_context = context_data or {}
        prompt = f"""
        Você é o analista financeiro de uma empresa. Responda perguntas sobre os dados fornecidos.
        Hoje é: {today}
        O chat é SOMENTE LEITURA: nunca proponha confirmar, lançar, cadastrar, alterar ou excluir dados.
        Se o usuário pedir um lançamento, explique que deve usar as abas Lançamentos, Estoque ou Gerenciar.
        Use apenas os dados do contexto. Não invente valores. Informe o período usado e, quando útil, mostre a conta do cálculo.
        Responda em português do Brasil, de forma objetiva e com valores em R$.

        CONTEXTO FINANCEIRO:
        {json.dumps(sanitize_data(data_context), ensure_ascii=False)}

        PERGUNTA DO USUÁRIO: "{user_input}"
        """

        response = model.generate_content(prompt)
        return {"status": "ANSWERED", "answer": response.text.strip()}
    
    except Exception as e:
        return {"error": f"Erro na IA: {str(e)}"}

def generate_ai_reply(ai_response):
    """
    Gera a resposta em texto baseada no JSON da IA.
    """
    if "error" in ai_response:
        return ai_response["error"]
        
    if ai_response.get("status") == "ANSWERED":
        return ai_response.get("answer", "Não encontrei uma resposta para essa pergunta.")

    if ai_response.get("status") == "INCOMPLETE":
        # Se falta algo, faz a primeira pergunta da lista
        return ai_response.get("missing_fields", ["Pode me dar mais detalhes?"])[0]
    
    intent = ai_response.get("intent")
    data = ai_response.get("data", {})
    
    msg = f"Ok! Entendi que você quer registrar: **{intent}**.\n"
    msg += f"- **Valor:** R$ {data.get('amount', 0):.2f}\n"
    if data.get('description'): msg += f"- **Descrição:** {data['description']}\n"
    
    return msg + "\nPosso confirmar o lançamento?"

def process_statement(file_content, entities_context=None):
    """
    Processa o conteúdo bruto de um arquivo (CSV/TXT/Excel convertido) e retorna uma lista 
    de ações ERP estruturadas (Vendas, Estoque, Financeiro).
    """
    if not configure_genai():
        return {"error": "API Key não configurada."}

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        today = date.today().isoformat()
        entities_str = f"\nEntidades Existentes: {json.dumps(sanitize_data(entities_context))}" if entities_context else ""

        prompt = f"""
        Você é um analista de dados especialista em ERP. Sua missão é ler o conteúdo de uma planilha e extrair TODAS as movimentações.
        Hoje é: {today} {entities_str}
        
        REGRAS OBRIGATÓRIAS DE TIPO (CRÍTICO - NUNCA VIOLÁ-LAS):
        - O campo "type" DEVE ser EXATAMENTE "Receita" OU "Despesa". NUNCA outro valor.
        - "Receita": dinheiro que ENTROU no caixa. Ex: recebimento de venda, serviço pago.
        - "Despesa": dinheiro que SAIU do caixa. Ex: aluguel, compra de insumo, combustível, salário, qualquer custo/gasto.
        - Se a linha tem palavras como: "compra", "pagamento", "custo", "aluguel", "salário", "despesa", "gasto" -> type = "Despesa"
        - O campo "category" é SEPARADO e pode ter qualquer texto descritivo da categoria original.
        
        REGRAS DE INTENÇÃO:
        1. Se a linha contiver "venda", "cupom", "cliente", "pedido" -> Intent: `REGISTER_SALE`
        2. Se a linha contiver "entrada estoque", "fornecedor", "chegada de mercadoria" -> Intent: `STOCK_MOVEMENT` (type='in')
        3. Se for qualquer saída de caixa (custos, despesas) -> Intent: `SAVE_TRANSACTION`, type = "Despesa"
        4. Se for receita/entrada de caixa genérica -> Intent: `SAVE_TRANSACTION`, type = "Receita"
        5. Aporte de sócio -> `PARTNER_CONTRIBUTION` | Retirada de sócio -> `PARTNER_WITHDRAWAL`
        
        MAPEAMENTO DE PRODUTOS:
        - Se identificar um nome de produto, procure nas 'Entidades Existentes'. Se achar, use o 'product_id'.
        
        DADOS DA PLANILHA:
        ---
        {file_content[:15000]}
        ---
        
        SAÍDA (JSON Puro - Lista de Intenções):
        [
            {{
                "intent": "SAVE_TRANSACTION",
                "data": {{
                    "date": "YYYY-MM-DD",
                    "amount": 100.00,
                    "description": "Aluguel Sala",
                    "type": "Despesa",
                    "category": "Custos Fixos",
                    "quantity": null,
                    "product_id": null
                }}
            }},
            ...
        ]
        """

        response = model.generate_content(prompt)
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        
        # Tenta sanitizar se o JSON vier quebrado
        if not text_response.startswith('['):
            # Procura o primeiro [ e o último ]
            start = text_response.find('[')
            end = text_response.rfind(']') + 1
            if start != -1 and end != 0:
                text_response = text_response[start:end]

        return json.loads(text_response)
    
    except Exception as e:
        return {"error": f"Erro processando dados: {str(e)}"}
