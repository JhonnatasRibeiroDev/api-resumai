# ResumAi API

API backend do **ResumAi**: recebe PDFs, extrai o texto, gera resumos com o
Gemini e processa tudo de forma **assíncrona** usando Celery + RabbitMQ. Também
gera "resumos integrados" combinando o conteúdo de vários documentos em um só.

Este repositório é o backend do projeto. O frontend (Next.js) vive em um
repositório separado, [`ui-resumai`](../ui-resumai), e se conecta a esta API
via HTTP.

## Sumário

- [Visão geral](#visão-geral)
- [Tecnologias usadas](#tecnologias-usadas)
- [Arquitetura](#arquitetura)
- [Fluxo assíncrono de resumo](#fluxo-assíncrono-de-resumo)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Modelo de dados](#modelo-de-dados)
- [Referência da API](#referência-da-api)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Instalação e execução](#instalação-e-execução)
- [Autenticação no Swagger](#autenticação-no-swagger)
- [Testes](#testes)

## Visão geral

O fluxo principal do sistema é:

1. O usuário se cadastra/loga e recebe um JWT.
2. Faz upload de um PDF — o texto é extraído no momento do upload (PyMuPDF).
3. Dispara um resumo (de um documento, ou "integrado" de vários documentos).
   A API **não gera o resumo na hora**: cria um `SummaryJob` com status
   `pending` e responde `202 Accepted` imediatamente.
4. Um worker Celery, consumindo uma fila no RabbitMQ, pega o job, chama a
   LLM (Gemini) e grava o resultado.
5. O cliente consulta o status do job (`GET /summary-jobs/{job_id}`) até virar
   `completed` (resumo pronto) ou `failed` (com opção de `retry`).

Esse desenho evita bloquear a requisição HTTP enquanto a LLM processa textos
potencialmente longos (o texto é dividido em chunks — veja
[`SUMMARY_CHUNK_CHARS`](#variáveis-de-ambiente) — quando excede o limite de
caracteres por chamada).

## Tecnologias usadas

| Tecnologia | Versão | Papel |
|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | 0.115.6 | Framework web / definição das rotas e schemas |
| [Uvicorn](https://www.uvicorn.org/) | 0.34.0 | Servidor ASGI |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0.36 | ORM |
| [Alembic](https://alembic.sqlalchemy.org/) | 1.14.0 | Migrations do banco |
| [PostgreSQL](https://www.postgresql.org/) | 16 (imagem Docker) | Banco de dados relacional |
| [psycopg](https://www.psycopg.org/psycopg3/) | 3.2.3 | Driver PostgreSQL |
| [Celery](https://docs.celeryq.dev/) | 5.4.0 | Fila de processamento assíncrono dos resumos |
| [RabbitMQ](https://www.rabbitmq.com/) | 3-management (imagem Docker) | Broker de mensagens do Celery |
| [google-genai](https://pypi.org/project/google-genai/) | 0.5.0 | Cliente da API do Gemini (geração dos resumos) |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | 1.25.1 | Extração de texto dos PDFs enviados |
| [python-jose](https://github.com/mpdavis/python-jose) | 3.3.0 | Geração/validação de JWT |
| [passlib](https://passlib.readthedocs.io/) + [bcrypt](https://pypi.org/project/bcrypt/) | 1.7.4 / 4.0.1 | Hash de senhas |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | 2.7.1 | Configuração via variáveis de ambiente |
| [pytest](https://docs.pytest.org/) + [httpx](https://www.python-httpx.org/) | 8.3.4 / 0.28.1 | Testes automatizados |

## Arquitetura

```mermaid
flowchart TB
    subgraph Cliente
        UI["Frontend (ui-resumai)"]
        Swagger["Swagger UI /api/v1/docs"]
    end

    subgraph "api-resumai (Docker Compose)"
        API["FastAPI (api)\nporta 8000"]
        Worker["Celery Worker"]
        MQ[("RabbitMQ")]
        DB[("PostgreSQL 16")]
    end

    Gemini["Gemini API (LLM)"]

    UI -->|"HTTP + JWT"| API
    Swagger -->|"HTTP + JWT"| API
    API -->|"CRUD (users, documents, summaries)"| DB
    API -->|"enfileira SummaryJob"| MQ
    MQ -->|"consome job"| Worker
    Worker -->|"lê/atualiza"| DB
    Worker -->|"gera resumo"| Gemini
```

Os quatro serviços (`postgres`, `rabbitmq`, `api`, `worker`) são definidos no
`docker-compose.yml` e compartilham a rede `resumai_network`.

## Fluxo assíncrono de resumo

```mermaid
sequenceDiagram
    actor Cliente
    participant API as FastAPI
    participant DB as PostgreSQL
    participant MQ as RabbitMQ
    participant Worker as Celery Worker
    participant Gemini as Gemini API

    Cliente->>API: POST /documents/{id}/summarize
    API->>DB: cria SummaryJob (status=pending)
    API->>MQ: publica summary.process(job_id)
    API-->>Cliente: 202 Accepted (SummaryJob pending)

    MQ->>Worker: entrega a task
    Worker->>DB: marca job como processing
    Worker->>Gemini: envia texto (em chunks, se necessário)
    Gemini-->>Worker: resumo gerado
    Worker->>DB: grava Summary e marca job como completed

    loop Polling do cliente
        Cliente->>API: GET /summary-jobs/{job_id}
        API-->>Cliente: status atual (pending/processing/completed/failed)
    end
```

Se o job falhar (erro da LLM, PDF inválido etc.), o worker marca o
`SummaryJob` como `failed` com `error_message`. O cliente pode reprocessar com
`POST /summary-jobs/{job_id}/retry`, respeitando o limite de tentativas
(`SUMMARY_MAX_ATTEMPTS`) e o limite de jobs ativos simultâneos por usuário
(`USER_MAX_ACTIVE_SUMMARY_JOBS`).

O mesmo mecanismo de job é usado para o **resumo integrado**
(`POST /summaries/integrated`), que combina o texto de vários documentos do
usuário em um único resumo.

## Estrutura do projeto

```
api-resumai/
├── app/
│   ├── main.py              # instancia o FastAPI, CORS, /health, monta os routers
│   ├── auth/                # registro/login, geração de JWT (routes, service, schemas)
│   ├── users/               # perfil do usuário (GET/PATCH /users/me)
│   ├── documents/           # upload, listagem e remoção de PDFs
│   ├── summaries/
│   │   ├── models.py        # Summary, IntegratedSummary, SummaryJob
│   │   ├── processor.py     # lógica de processamento do job (chamada à LLM, chunking)
│   │   ├── constants.py
│   │   ├── service.py       # criação/consulta/retry de jobs e resumos
│   │   └── routes.py
│   ├── dashboard/           # estatísticas agregadas do usuário
│   ├── llm/
│   │   ├── client.py        # GeminiLLMClient
│   │   └── prompts.py       # prompts usados na geração dos resumos
│   ├── worker/
│   │   ├── celery_app.py    # configuração da app Celery
│   │   └── tasks.py         # task summary.process
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   └── security.py      # hash de senha, criação/validação de JWT
│   ├── db/                  # engine, sessão, base declarativa
│   └── utils/pdf.py         # extração de texto do PDF (PyMuPDF)
├── alembic/                  # migrations (initial_schema, summary_jobs, backfill_summary_model_names)
├── tests/                    # suíte pytest
├── uploads/                  # PDFs enviados (montado como volume no Docker)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Modelo de dados

| Tabela | Descrição |
|---|---|
| `users` | Conta do usuário (email/nome de usuário, senha com hash) |
| `documents` | PDF enviado + texto extraído, vinculado ao usuário |
| `summaries` | Resumo gerado para um documento específico |
| `integrated_summaries` | Resumo combinando múltiplos documentos |
| `summary_jobs` | Job de processamento assíncrono (`kind`, `status`, `attempt_count`, `error_message`, ligado a um `Summary`/`IntegratedSummary`) |

## Referência da API

Todas as rotas (exceto `/health`) ficam sob o prefixo `/api/v1` e exigem JWT
(`Authorization: Bearer <token>`), exceto registro e login.

| Método | Rota | Status de sucesso | Auth | Descrição |
|---|---|---|---|---|
| GET | `/health` | 200 | não | Health check simples |
| POST | `/api/v1/auth/register` | 201 | não | Cria um novo usuário |
| POST | `/api/v1/auth/login` | 200 | não | Autentica e retorna um `access_token` (JWT) |
| GET | `/api/v1/users/me` | 200 | sim | Dados do usuário autenticado |
| PATCH | `/api/v1/users/me` | 200 | sim | Atualiza o perfil do usuário autenticado |
| POST | `/api/v1/documents/upload` | 201 | sim | Envia um PDF (`multipart/form-data`), extrai o texto |
| GET | `/api/v1/documents` | 200 | sim | Lista os documentos do usuário |
| GET | `/api/v1/documents/{document_id}` | 200 | sim | Detalhe de um documento |
| DELETE | `/api/v1/documents/{document_id}` | 204 | sim | Remove um documento |
| POST | `/api/v1/documents/{document_id}/summarize` | 202 | sim | Cria um `SummaryJob` para resumir o documento |
| GET | `/api/v1/documents/{document_id}/summary` | 200 | sim | Retorna o resumo já gerado do documento |
| GET | `/api/v1/summary-jobs/{job_id}` | 200 | sim | Consulta o status de um job (para *polling*) |
| POST | `/api/v1/summary-jobs/{job_id}/retry` | 200 | sim | Reprocessa um job que falhou |
| POST | `/api/v1/summaries/integrated` | 202 | sim | Cria um job de resumo integrado de vários documentos |
| GET | `/api/v1/summaries/integrated` | 200 | sim | Lista os resumos integrados do usuário |
| GET | `/api/v1/summaries/integrated/{summary_id}` | 200 | sim | Detalhe de um resumo integrado |
| GET | `/api/v1/dashboard` | 200 | sim | Estatísticas agregadas (documentos, resumos, jobs) |

Documentação interativa:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Variáveis de ambiente

Use `api-resumai/.env.example` como referência para criar seu `.env`. Todos os
valores abaixo têm default em `app/core/config.py`, então nada é
estritamente obrigatório para subir a API — exceto `GEMINI_API_KEY` se você
quiser resumos reais.

| Variável | Default | Descrição |
|---|---|---|
| `APP_NAME` | `ResumAi API` | Nome exibido no OpenAPI |
| `APP_ENV` | `development` | Ambiente da aplicação |
| `DATABASE_URL` | `postgresql+psycopg://resumai:resumai_password@postgres:5432/resumai` | String de conexão do PostgreSQL |
| `JWT_SECRET` | `change_this_secret` | Segredo usado para assinar os JWT — **troque em produção** |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de assinatura do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Validade do token de acesso |
| `UPLOAD_DIR` | `/app/uploads` | Diretório onde os PDFs enviados são salvos |
| `MAX_UPLOAD_SIZE_MB` | `50` | Tamanho máximo de upload permitido |
| `MAX_LLM_CHARS` | `30000` | Limite de caracteres enviados por chamada à LLM |
| `SUMMARY_CHUNK_CHARS` | `12000` | Tamanho de cada chunk quando o texto é dividido |
| `SUMMARY_CHUNK_OVERLAP_CHARS` | `500` | Sobreposição entre chunks consecutivos |
| `SUMMARY_MAX_CHUNKS` | `20` | Número máximo de chunks processados por documento |
| `USER_MAX_ACTIVE_SUMMARY_JOBS` | `2` | Limite de jobs simultâneos ativos por usuário |
| `SUMMARY_MAX_ATTEMPTS` | `3` | Número máximo de tentativas (incluindo retries) por job |
| `GEMINI_API_KEY` | *(vazio)* | Chave de API do Gemini — necessária para gerar resumos reais |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modelo do Gemini usado |
| `CELERY_BROKER_URL` | `amqp://resumai:resumai_password@rabbitmq:5672//` | URL de conexão do broker (RabbitMQ) |

## Instalação e execução

### Docker (recomendado)

Dentro da pasta `api-resumai`:

```bash
docker compose up --build
```

Isso sobe 4 serviços: `postgres`, `rabbitmq`, `api` (roda
`alembic upgrade head` automaticamente antes de subir o Uvicorn) e `worker`
(processo Celery). A API fica disponível em `http://localhost:8000`.

Para gerar resumos reais (em vez de jobs que falham por falta de LLM), defina
antes de subir a stack:

```bash
export GEMINI_API_KEY="sua-chave"
```

Sem `GEMINI_API_KEY`, o health check, cadastro, login e upload funcionam
normalmente — apenas os jobs de resumo serão criados e o worker os marcará
como `failed` com a mensagem de erro da LLM.

### Local, sem Docker

Requer Python 3.12, PostgreSQL e RabbitMQ acessíveis (podem ser os mesmos
containers do `docker-compose.yml`, subindo só `postgres` e `rabbitmq`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # ajuste DATABASE_URL / CELERY_BROKER_URL se necessário

alembic upgrade head
uvicorn app.main:app --reload
```

Em outro terminal, suba o worker Celery:

```bash
celery -A app.worker.celery_app.celery_app worker --loglevel=info
```

## Autenticação no Swagger

No botão **Authorize** do Swagger UI, cole apenas o `access_token` retornado
por `POST /api/v1/auth/login` — **sem** o prefixo `Bearer`; o Swagger adiciona
isso automaticamente.

## Testes

```bash
pytest
```

A suíte (`tests/`) usa SQLite em memória e um `FakeLLMClient` configurados em
`tests/conftest.py`, então roda sem precisar de PostgreSQL, RabbitMQ ou uma
`GEMINI_API_KEY` real. Arquivos de teste:

- `test_api_flow.py` — fluxo ponta a ponta da API
- `test_pdf.py` — extração de texto de PDF
- `test_prompts.py` — construção dos prompts enviados à LLM
- `test_security.py` — hash de senha e JWT
- `test_summary_jobs.py` — criação, processamento e retry de jobs
- `test_worker_model_registry.py` — registro de tasks do Celery
