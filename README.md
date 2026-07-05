# ResumAi API

API FastAPI para upload, extração de texto e resumo assíncrono de PDFs com Gemini,
Celery e RabbitMQ.

## Rodando com Docker

Dentro da pasta `api-resumai`:

```bash
docker compose up --build
```

A stack sobe PostgreSQL, RabbitMQ, API e worker Celery. A API ficará disponível em
`http://localhost:8000`.

Documentação:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
- ReDoc: `http://localhost:8000/api/v1/redoc`

No botão `Authorize` do Swagger, cole o `access_token` retornado por `POST /api/v1/auth/login`. Não inclua o prefixo `Bearer`; o Swagger adiciona isso sozinho.

## Variáveis

Use `api-resumai/.env.example` como referência. Para gerar resumos reais, defina:

```bash
export GEMINI_API_KEY="sua-chave"
```

Sem `GEMINI_API_KEY`, o health check, cadastro, login e upload funcionam. Jobs de
resumo serão criados, mas o worker marcará o job como `failed` com a mensagem de
erro da LLM.

## Rotas principais

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `POST /api/v1/documents/{document_id}/summarize`
- `GET /api/v1/summary-jobs/{job_id}`
- `POST /api/v1/summary-jobs/{job_id}/retry`
- `POST /api/v1/summaries/integrated`
- `GET /api/v1/dashboard`

Os endpoints de criação de resumo retornam `202 Accepted` com um job em vez do
resumo final. Consulte `GET /api/v1/summary-jobs/{job_id}` até o status virar
`completed` ou `failed`.
