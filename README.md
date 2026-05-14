# GenAI Data Assistant

> A fully local, production-style **Retrieval-Augmented Generation (RAG)** platform that lets users chat with their own **PDF, CSV, and Excel** files — powered by **Ollama (Llama 3.1 8B)**, **pgvector**, **LangChain**, **FastAPI**, and **Streamlit**, with a complete **JWT auth + token-quota** system.

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white">
  <img src="https://img.shields.io/badge/LangChain-1.x-1C3C3C?logo=langchain&logoColor=white">
  <img src="https://img.shields.io/badge/Ollama-Llama%203.1%208B-000000?logo=ollama&logoColor=white">
  <img src="https://img.shields.io/badge/pgvector-PostgreSQL%2016-336791?logo=postgresql&logoColor=white">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
  <img src="https://img.shields.io/badge/Auth-JWT-black?logo=jsonwebtokens&logoColor=white">
  <img src="https://img.shields.io/badge/License-MIT-green">
</p>

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Quick Start](#quick-start)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [How RAG Works Here](#how-rag-works-here)
10. [Testing](#testing)
11. [Roadmap](#roadmap)
12. [Author](#author)
13. [License](#license)

---

## Overview

**GenAI Data Assistant** is an end-to-end RAG application designed to demonstrate production-grade GenAI engineering practices on a fully **local, privacy-preserving stack** — no data ever leaves the user's machine.

Users can:

- Sign up / log in with **JWT-secured** accounts.
- Upload **PDF, CSV, or Excel** documents.
- Ask natural-language questions about their files.
- Receive grounded, citation-aware answers from a **local Llama 3.1 8B** model.
- Track usage through an integrated **token-quota system** with an **admin approval workflow**.

The project is intentionally structured like a real product — clean module boundaries, container-first deployment, automated tests, and a polished Streamlit UI.

---

## Key Features

- **Local-first RAG pipeline** – PDF / CSV / Excel ingestion → chunking → `nomic-embed-text` embeddings → `pgvector` search → Llama 3.1 8B generation.
- **Multi-format ingestion** – Dedicated loaders for PDFs, CSVs, and Excel sheets, with normalized chunking.
- **Conversational memory** – Per-user `ChatSession` stores history so follow-up questions resolve correctly.
- **JWT authentication** – Bcrypt-hashed passwords, signed JWTs, role-aware endpoints.
- **Token-quota system** – Each query costs tokens; users can submit top-up requests; admins approve/reject or allocate directly.
- **Admin console** – Manage users, view pending requests, allocate or revoke tokens.
- **FastAPI backend** – Clean REST surface with OpenAPI docs at `/docs`.
- **Streamlit UI** – Login, chat, file upload, quota bar, admin panel.
- **Dockerized** – One `docker compose up` brings up Postgres + pgvector + API + UI.
- **Tested** – Pytest suite for retrieval and RAG flow.

---

## Architecture

```
                 ┌───────────────────────────┐
                 │        Streamlit UI       │
                 │ (login · chat · uploads)  │
                 └─────────────┬─────────────┘
                               │  HTTPS + JWT
                               ▼
                 ┌───────────────────────────┐
                 │         FastAPI           │
                 │  /register /login /ask    │
                 │  /upload  /admin/* ...    │
                 └──────┬───────────┬────────┘
                        │           │
            ingestion   │           │  chat / RAG
                        ▼           ▼
              ┌───────────────┐  ┌────────────────────┐
              │  Loaders +    │  │  LangChain RAG     │
              │  Splitter     │  │  (retriever +      │
              │ (PDF/CSV/XLS) │  │   prompt + LLM)    │
              └──────┬────────┘  └─────────┬──────────┘
                     │                     │
                     ▼                     ▼
            ┌───────────────────┐   ┌─────────────────┐
            │   nomic-embed     │   │  llama3.1:8b    │
            │   (Ollama)        │   │  (Ollama)       │
            └─────────┬─────────┘   └─────────────────┘
                      │
                      ▼
            ┌───────────────────────────────┐
            │  PostgreSQL 16 + pgvector     │
            │  documents · users · tokens   │
            └───────────────────────────────┘
```

---

## Tech Stack

| Layer            | Technology                                                            |
| ---------------- | --------------------------------------------------------------------- |
| **LLM**          | Ollama – `llama3.1:8b`                                                |
| **Embeddings**   | Ollama – `nomic-embed-text` (768-dim)                                 |
| **Vector store** | PostgreSQL 16 + `pgvector`                                            |
| **Orchestration**| LangChain (loaders, splitters, retrievers, RAG chain)                 |
| **Backend API**  | FastAPI + Uvicorn                                                     |
| **Frontend**     | Streamlit                                                             |
| **Auth**         | JWT (PyJWT) + bcrypt password hashing                                 |
| **Database**     | PostgreSQL 16 (also stores users, sessions, token quotas)             |
| **Infra**        | Docker + Docker Compose                                               |
| **Tests**        | Pytest                                                                |

---

## Project Structure

```
genai-data-assistant/
├── api/                # FastAPI app & route handlers
│   └── main.py
├── auth/               # JWT, password hashing, user/token models
│   ├── models.py
│   └── utils.py
├── ingestion/          # Document loaders + ingestion pipeline
│   ├── pdf_loader.py
│   ├── csv_loader.py
│   ├── loader.py
│   └── pipeline.py
├── embeddings/         # Ollama embedding wrapper
│   └── embedder.py
├── vectorstore/        # pgvector setup + similarity search
│   └── store.py
├── llm/                # Prompts, RAG chain, conversational session
│   ├── prompts.py
│   ├── rag_chain.py
│   └── session.py
├── ui/                 # Streamlit front-end
│   └── app.py
├── tests/              # Pytest suite
│   ├── test_rag.py
│   └── test_search.py
├── data/               # Sample + uploaded documents (gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### Option 1 — Docker (recommended)

> Requires Docker Desktop, plus Ollama running on the **host** machine.

```bash
# 1. Clone
git clone https://github.com/saikiran3344/genai-data-assistant.git
cd genai-data-assistant

# 2. Configure
cp .env.example .env          # then edit values as needed

# 3. Pull the local models (host-side Ollama)
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 4. Launch the stack
docker compose up --build
```

Then open:

- **Streamlit UI** → http://localhost:8501
- **FastAPI docs** → http://localhost:8000/docs

### Option 2 — Local Python

```bash
git clone https://github.com/saikiran3344/genai-data-assistant.git
cd genai-data-assistant
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start Postgres+pgvector via Docker (or use a local install)
docker run -d --name pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=genai_db \
  -p 5432:5432 pgvector/pgvector:pg16

# Run backend + frontend in two terminals
uvicorn api.main:app --reload
streamlit run ui/app.py
```

---

## Configuration

All configuration lives in a `.env` file. See [`.env.example`](.env.example) for the full list. The most important variables:

| Variable             | Purpose                                                       |
| -------------------- | ------------------------------------------------------------- |
| `DB_*`               | PostgreSQL connection settings                                |
| `OLLAMA_BASE_URL`    | Ollama endpoint (`host.docker.internal` when API is in Docker)|
| `OLLAMA_LLM_MODEL`   | Generation model (default `llama3.1:8b`)                      |
| `OLLAMA_EMBED_MODEL` | Embedding model (default `nomic-embed-text`)                  |
| `JWT_SECRET_KEY`     | Secret used to sign auth tokens — **change in production**    |
| `DEFAULT_TOKENS`     | Tokens granted to a new user on registration                  |

---

## API Reference

The FastAPI service exposes a clean, fully documented REST surface (see `/docs` for live OpenAPI):

| Method | Endpoint                                  | Description                                |
| ------ | ----------------------------------------- | ------------------------------------------ |
| POST   | `/register`                               | Create a new user                          |
| POST   | `/login`                                  | Obtain a JWT access token                  |
| GET    | `/me`                                     | Current user profile                       |
| POST   | `/ask`                                    | Ask a question (RAG)                       |
| POST   | `/upload`                                 | Upload a PDF / CSV / Excel                 |
| GET    | `/token-status`                           | Remaining token quota                      |
| POST   | `/request-tokens`                         | Submit a top-up request                    |
| POST   | `/clear-history`                          | Reset the user's conversation              |
| GET    | `/admin/users`                            | List all users *(admin)*                   |
| GET    | `/admin/requests`                         | Pending token requests *(admin)*           |
| POST   | `/admin/requests/{id}/approve`            | Approve request *(admin)*                  |
| POST   | `/admin/requests/{id}/reject`             | Reject request *(admin)*                   |
| POST   | `/admin/allocate`                         | Allocate tokens directly *(admin)*         |
| PUT    | `/admin/users/{id}/deactivate`            | Deactivate a user *(admin)*                |
| GET    | `/health`                                 | Liveness probe                             |
| GET    | `/stats`                                  | Index / chunk count                        |

---

## How RAG Works Here

1. **Ingest** – Files dropped into `/upload` are routed by extension to a dedicated loader (PDF, CSV, Excel), then split into overlapping chunks.
2. **Embed** – Each chunk is embedded with `nomic-embed-text` via Ollama (no external API calls).
3. **Index** – Embeddings + metadata are stored in PostgreSQL using the `pgvector` extension.
4. **Retrieve** – On a question, the top-K most similar chunks are pulled via cosine similarity.
5. **Generate** – Retrieved context + chat history + the user's question are formatted by a curated prompt template and sent to `llama3.1:8b`.
6. **Account** – The request decrements the user's token quota; admins can approve top-up requests.

---

## Testing

```bash
pytest -v
```

The test suite covers:

- Vector retrieval correctness (`tests/test_search.py`)
- End-to-end RAG response shape (`tests/test_rag.py`)

---

## Roadmap

- [ ] Streaming responses in the Streamlit UI.
- [ ] Hybrid search (BM25 + dense) for better recall on tabular data.
- [ ] Per-document access control.
- [ ] Observability: request tracing + Prometheus metrics.
- [ ] Optional cloud-LLM fallback (Anthropic / OpenAI) behind a feature flag.
- [ ] CI pipeline (GitHub Actions) running lint + tests on every PR.

---

## Author

**Sai Kiran Reddy Nakka**
GenAI / Backend Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Sai%20Kiran%20Reddy%20Nakka-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sai-kiran-reddy-n-1bb00028a)
[![GitHub](https://img.shields.io/badge/GitHub-saikiran3344-181717?logo=github&logoColor=white)](https://github.com/saikiran3344)

> Open to GenAI / ML / Backend engineering opportunities. Reach out on LinkedIn.

---

## License

Released under the [MIT License](LICENSE).
