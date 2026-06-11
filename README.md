# SME AI Agent

> A multi-tenant AI-powered sales agent for Thai SME businesses — plug into LINE, reply instantly, remember every conversation.

---

## What it does

SME AI Agent connects to your LINE Official Account and handles customer conversations automatically. Each shop gets its own isolated bot with its own knowledge base, conversation memory, and token budget.

- Replies to LINE messages in natural Thai
- Remembers conversation history per user
- Knows your products, FAQs, and shop policies
- Tracks token usage and cost per shop
- Scales across multiple shops on a single backend

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Python 3.11 |
| Database | Supabase (PostgreSQL) |
| AI | Gemini 2.5 Flash-Lite via LangChain |
| Observability | Langfuse |
| Messaging | LINE Messaging API |
| Infra | Railway |
| CI/CD | GitHub Actions |

---

## Architecture

```
LINE User
    │
    ▼
LINE Messaging API
    │  POST /webhook/line/{shop_id}
    ▼
FastAPI (Railway)
    │
    ├── Verify signature (per-shop LINE secret)
    ├── Load shop from Supabase
    │
    ▼
LangChain Agent
    │
    ├── Build knowledge base (products + FAQs + policies)
    ├── Gemini Context Cache (if content ≥ 2048 tokens)
    ├── Conversation memory (sliding window, 10 turns)
    │
    ▼
Gemini 2.5 Flash-Lite
    │
    ▼
Reply via LINE API
    │
    ▼
Log token usage → Supabase token_usage table
```

---

## Getting Started

### Prerequisites

- Python 3.11
- [Supabase](https://supabase.com) project
- [Gemini API key](https://aistudio.google.com)
- [Langfuse](https://langfuse.com) account
- [LINE Developers](https://developers.line.biz) channel

### 1. Clone and install

```bash
git clone https://github.com/your-org/sme-ai-agent
cd sme-ai-agent
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
JWT_SECRET=your_jwt_secret

GEMINI_API_KEY=your_gemini_key

LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com

LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
LINE_BOT_USER_ID=your_line_bot_user_id
```

### 3. Set up database

Run these in Supabase SQL Editor:

```sql
CREATE TABLE shops (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    line_channel_id text,
    line_channel_secret text,
    line_channel_access_token text,
    plan text,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE users (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id uuid REFERENCES shops(id),
    email text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE products (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id uuid NOT NULL REFERENCES shops(id),
    name text NOT NULL,
    description text,
    price numeric(10,2),
    stock integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE faqs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id uuid NOT NULL REFERENCES shops(id),
    question text NOT NULL,
    answer text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE shop_policies (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id uuid NOT NULL REFERENCES shops(id),
    shipping_policy text,
    return_policy text,
    payment_methods text,
    business_hours text,
    about text,
    custom_instructions text,
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE token_usage (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id uuid NOT NULL,
    session_id text,
    model text,
    input_tokens integer DEFAULT 0,
    output_tokens integer DEFAULT 0,
    cached_tokens integer DEFAULT 0,
    cost_usd numeric(10,8) DEFAULT 0,
    cache_hit boolean DEFAULT false,
    latency_ms integer,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE shop_quota (
    shop_id uuid PRIMARY KEY,
    monthly_tokens int8,
    used_tokens int8,
    alert_pct int4,
    reset_date date
);
```

### 4. Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

---

## API Reference

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register shop owner |
| POST | `/api/v1/auth/login` | Login and get JWT |

### Knowledge Base

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/knowledge/products` | Add a product |
| GET | `/api/v1/knowledge/products/{shop_id}` | List products |
| POST | `/api/v1/knowledge/faqs` | Add a FAQ |
| GET | `/api/v1/knowledge/faqs/{shop_id}` | List FAQs |
| PUT | `/api/v1/knowledge/policy/{shop_id}` | Update shop policy |
| GET | `/api/v1/knowledge/policy/{shop_id}` | Get shop policy |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/chat` | Send a message (requires JWT + X-Shop-Id) |

### Webhook

| Method | Endpoint | Description |
|---|---|---|
| POST | `/webhook/line/{shop_id}` | LINE webhook endpoint |

---

## Setting up a Shop

```bash
# 1. Register
curl -X POST "https://your-app.railway.app/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@shop.com", "password": "secret", "shop_id": "your-shop-uuid"}'

# 2. Login
curl -X POST "https://your-app.railway.app/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@shop.com", "password": "secret"}'

# 3. Add products
curl -X POST "https://your-app.railway.app/api/v1/knowledge/products?shop_id=your-shop-uuid" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "Leather Tote", "price": 1290, "stock": 50}'
```

Set LINE Webhook URL to:
```
https://your-app.railway.app/webhook/line/{shop_id}
```

---

## Project Structure

```
sme-ai-agent/
├── app/
│   ├── ai/
│   │   ├── agent.py          # LangChain agent + memory
│   │   ├── cache_manager.py  # Gemini context cache
│   │   └── gemini.py         # Raw Gemini SDK client
│   ├── routers/
│   │   ├── auth.py           # Register / Login
│   │   ├── chat.py           # Chat endpoint
│   │   ├── knowledge.py      # Products / FAQs / Policy
│   │   ├── shop.py           # Shop management
│   │   └── webhook.py        # LINE webhook
│   ├── services/
│   │   ├── knowledge.py      # Build knowledge base from DB
│   │   └── token_usage.py    # Log token usage to Supabase
│   ├── config.py             # Pydantic settings
│   ├── database.py           # Supabase client
│   ├── dependencies.py       # JWT auth + shop verification
│   └── main.py               # FastAPI app
├── tests/
│   └── test_health.py
├── .github/workflows/
│   └── ci.yml                # Test + deploy to Railway
├── .env.example
├── pytest.ini
└── requirements.txt
```

---

## Caching Strategy

The system uses a two-tier approach to minimize token costs:

**Gemini Context Cache** — When a shop's knowledge base exceeds 2,048 tokens, the system prompt and product data are uploaded once and cached for 1 hour. Subsequent requests only pay for new messages, not the full context.

**Fallback** — When content is below the threshold, the knowledge base is injected directly into the system prompt each request. The bot works identically; only token cost differs.

---

## Roadmap

- [x] Multi-tenant LINE webhook
- [x] LangChain agent with conversation memory
- [x] Knowledge base (products, FAQs, policies)
- [x] JWT authentication per shop
- [x] Gemini context cache with fallback
- [x] Token usage tracking via Langfuse + Supabase
- [x] CI/CD via GitHub Actions → Railway
- [ ] Token logger middleware wired into agent
- [ ] Shop quota enforcement
- [ ] RAG pipeline with Qdrant
- [ ] Semantic cache (Redis + vector similarity)
- [ ] Model routing (Flash-Lite vs Flash)
- [ ] Dashboard (Next.js)
- [ ] Billing system

---

## License

MIT