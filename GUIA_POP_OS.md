# Rodando no Pop!_OS sem perder os lancamentos

O projeto foi configurado para usar o banco SQLite local `financeiro_dev.db`, que atualmente contem os seus dados.

## Arquivos importantes

- Banco principal: `financeiro_dev.db`
- Backup de seguranca criado antes da configuracao local: `financeiro_dev.pre_local_setup.db`
- Configuracao local: `.env`

## Primeira execucao

No terminal, dentro da pasta do projeto:

```bash
chmod +x run_local_linux.sh
./run_local_linux.sh
```

Na primeira vez, o script cria `.venv`, instala as dependencias e inicializa o banco sem apagar os dados existentes.

## Acessar a aplicacao

Depois que o Streamlit iniciar, abra:

```text
http://127.0.0.1:8501
```

## Gemini API Key

Se quiser usar os recursos de IA no chat, preencha `GEMINI_API_KEY` no arquivo `.env`.
O restante do sistema continua apontando para o mesmo banco local.
