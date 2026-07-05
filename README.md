# ResumAi API

API FastAPI para upload, extração de texto e resumo de PDFs com Gemini.

## Rodando com Docker

Dentro da pasta `api-resumai`:

```bash
docker compose up --build
```

A API ficará disponível em `http://localhost:8000`.

## Variáveis

Use `api-resumai/.env.example` como referência. Para gerar resumos reais, defina:

```bash
export GEMINI_API_KEY="sua-chave"
```

Sem `GEMINI_API_KEY`, o health check, cadastro, login e upload funcionam, mas endpoints de resumo retornam `502`.

## Rotas principais

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `POST /api/v1/documents/{document_id}/summarize`
- `POST /api/v1/summaries/integrated`
- `GET /api/v1/dashboard`
