# PayPilot — Agentic Payment Recovery(originally Intelligent Research Agent)

> **Razorpay AI Buildathon — Track 03: AI Revenue Recovery**

PayPilot is an agentic payment recovery copilot for merchants. It investigates payment-performance degradation using transaction analytics, identifies the dominant failure pattern, retrieves recovery guidance from a separate RAG pipeline, and produces bounded, evidence-grounded recommendations with an auditable investigation record.

**Core workflow:** Detect → Diagnose → Retrieve Guidance → Recommend → Audit

---

## ⚠️ Important: Required RAG Dependency

**PayPilot does not run correctly as a standalone repository.**

The project depends on the separately built **Multitenant-RAG** pipeline for internal payment-recovery knowledge retrieval.

```text
PayPilot Agent
     │
     │ HTTP /retrieve
     ▼
Multitenant-RAG Pipeline
     │
     ▼
PostgreSQL + pgvector
```

Before running PayPilot, the RAG service must be running and reachable at:

```text
http://localhost:8000
```

Both `get_payment_recovery_guidance` and `search_knowledge_base` call this separate RAG service over HTTP.

> **The RAG system is NOT included in this repository. It is a separate project/service and must be started separately before PayPilot. Without the RAG pipeline, the RAG-dependent recovery workflow will not work.**

---

## 🎯 Problem

Payment failures can quickly become revenue losses, frustrated customers, and difficult-to-diagnose incidents.

A merchant might ask:

> **"My payment success rate dropped today. Investigate why and tell me what I should do."**

A generic LLM cannot reliably answer this because it needs access to both:

- actual payment-performance evidence, and
- internal recovery procedures.

PayPilot combines both through controlled agent tools.

---

## 💡 What Makes PayPilot Agentic?

PayPilot is not a hard-coded sequence of functions.

The LLM receives a set of tools and decides which tools are necessary based on the merchant's request and the results it observes.

```text
Merchant
   │
   ▼
PayPilot Agent
   │
   ├── get_payment_analytics
   │          │
   │          ▼
   │    Payment performance
   │    + failure analysis
   │
   ▼
Agent observes results
   │
   ├── get_payment_recovery_guidance
   │          │
   │          ▼
   │    Multitenant-RAG
   │          │
   │          ▼
   │    Grounded recovery guidance
   │
   ▼
Final recommendation
   │
   ▼
Audit record
```

For a payment degradation investigation, the system prompt tells the agent to begin with payment analytics and retrieve recovery guidance after a specific failure pattern has been identified. The actual tool calls are still selected by the LLM and visible in LangSmith.

---

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │       Merchant       │
                         │  "Payments dropped"  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      PayPilot        │
                         │     LangGraph        │
                         │    Agent / ReAct     │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌────────────────┐   ┌──────────────────┐   ┌────────────────┐
     │ Payment        │   │ Payment Recovery │   │ Calculator /   │
     │ Analytics      │   │ Guidance         │   │ Web Search     │
     └────────────────┘   └────────┬─────────┘   └────────────────┘
                                   │
                                   │ HTTP /retrieve
                                   ▼
                         ┌──────────────────────┐
                         │  Multitenant-RAG     │
                         │  Separate Service    │
                         │      :8000           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ PostgreSQL + pgvector│
                         │ Hybrid Retrieval     │
                         └──────────────────────┘

                         ┌──────────────────────┐
                         │      LangSmith       │
                         │ Agent + Tool Traces  │
                         └──────────────────────┘

                         ┌──────────────────────┐
                         │    Audit JSONL       │
                         │ Investigation Record │
                         └──────────────────────┘
```

---

## 🔄 Agent Reasoning Loop

PayPilot uses LangGraph to explicitly represent the agent/tool loop.

```python
builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "use_tool": "tools",
        "end": END
    }
)

builder.add_edge("tools", "agent")
```

The loop is:

1. The `agent` node sends the conversation and available tools to the LLM.
2. The LLM decides whether it needs a tool.
3. If a tool is requested, LangGraph routes execution to the `tools` node.
4. The tool result is added to the conversation.
5. The agent observes the result and decides what to do next.
6. The loop ends when the LLM produces a final response without another tool call.

This makes the agent's control flow explicit rather than hiding it inside a high-level agent executor.

---

## 🛠️ Tools

| Tool | Purpose |
|---|---|
| `get_payment_analytics` | Compares today's and yesterday's payment performance, including success rates, payment-method breakdowns, failure reasons, and transaction value at risk. |
| `get_payment_recovery_guidance` | Retrieves recovery guidance for an identified payment failure pattern from the separate Multitenant-RAG service. |
| `search_knowledge_base` | General internal knowledge retrieval through the separate RAG service. |
| `calculate` | Performs arithmetic when derived calculations are required. |
| `web_search` | Retrieves current external information when web context is required. |

The payment-specific tools form the core Track 03 workflow:

```text
get_payment_analytics
        ↓
identify failure pattern
        ↓
get_payment_recovery_guidance
        ↓
bounded recommendation
```

---

## 📊 Example Investigation

The demonstration uses a deterministic synthetic transaction dataset for September 2 and September 3, 2026, with intentionally degraded UPI performance on September 3.

For:

> **"My payment success rate dropped today. Investigate why and tell me what I should do."**

PayPilot identifies:

| Metric | Today | Yesterday | Change |
|---|---:|---:|---:|
| Overall success rate | 86.3% | 91.4% | -5.1 pp |
| UPI success rate | 66.7% | 90.7% | -24.0 pp |
| Failed transaction value | ₹11,29,259 | — | At risk |

The dominant failure category is timeout:

- **19 timeout failures**
- **46.3% of today's failures**

The agent then retrieves recovery guidance from the separate RAG pipeline and recommends evidence-grounded actions such as:

1. Review PSP response-time logs.
2. If provider-side latency is confirmed, consider routing new UPI transactions through a configured backup PSP/UPI route.
3. Limit automatic retries according to the retrieved recovery policy.
4. Apply appropriate customer-facing fallbacks for other failure categories.

**These are synthetic demonstration numbers, not live Razorpay production data.**

---

## 🧠 Grounded Recovery

PayPilot deliberately separates **observed facts** from **recommended actions**.

The agent is instructed not to invent:

- payment metrics,
- financial figures,
- SLAs,
- thresholds,
- timeout values,
- retry limits,
- monitoring percentages,
- deadlines,
- targets,
- owners,
- or operational policies.

Recovery recommendations should remain within the guidance retrieved from the internal RAG knowledge base.

PayPilot also does **not** claim to have recovered money or executed a financial action unless an execution tool explicitly reports that action.

The current prototype is therefore a **decision-support and recovery-recommendation system**, not a live payment execution system.

---

## 🧾 Audit Trail

Each investigation is written to:

```text
audit/audit_log.jsonl
```

Example:

```json
{
  "timestamp": "...",
  "user_query": "...",
  "tools_used": [
    "get_payment_analytics",
    "get_payment_recovery_guidance"
  ],
  "final_response": "...",
  "recovery_executed": false
}
```

This records:

- what the merchant asked,
- which tools were used,
- what recommendation was produced,
- whether a recovery action was actually executed.

`recovery_executed` remains `false` because the current prototype does not execute real financial recovery actions.

---

## 🔍 Observability

PayPilot uses **LangSmith** for end-to-end tracing.

A typical investigation can appear as:

```text
agent
 └── get_payment_analytics
      └── agent
           └── get_payment_recovery_guidance
                └── agent
                     └── final response
```

The trace makes the agent's decisions inspectable, including tool calls, arguments, results, model invocations, latency, and token usage.

This provides evidence that the workflow is an actual agentic tool-calling loop rather than a hard-coded function chain.

---

## 🧩 Relationship With Multitenant-RAG

PayPilot intentionally reuses a separate RAG system instead of duplicating retrieval inside the agent.

### Multitenant-RAG

Responsible for:

- document ingestion,
- chunking,
- embeddings,
- hybrid retrieval,
- pgvector search,
- tenant isolation,
- reranking,
- retrieval API.

### PayPilot

Responsible for:

- agent orchestration,
- payment analytics,
- tool selection,
- recovery investigation,
- recommendation generation,
- audit logging,
- observability.

They communicate through:

```text
POST http://localhost:8000/retrieve
```

This separation keeps the retrieval infrastructure reusable and lets PayPilot focus on decision-making.

---

## 📁 Project Structure

```text
PayPilot/
├── agent/
│   ├── graph.py
│   ├── tools.py
│   ├── commerce_tools.py
│   ├── commerce_data.py
│   ├── memory.py
│   ├── audit.py
│   └── quickdbcheck.py
│
├── audit/
│   └── audit_log.jsonl
│
├── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
└── README.md
```

---

# 🚀 Setup

## Prerequisites

### Required

- Python 3.13+
- Running **Multitenant-RAG** service
- PostgreSQL + pgvector for the RAG system
- Groq API key

### Optional

- Tavily API key — for `web_search`
- LangSmith API key — for tracing

---

## 1. Start Multitenant-RAG first

Clone and configure the separate Multitenant-RAG project.

Its API must be reachable at:

```text
http://localhost:8000
```

Verify it:

```bash
curl http://localhost:8000/health
```

> **Do this before starting PayPilot. The PayPilot recovery-guidance workflow depends on this service.**

---

## 2. Clone PayPilot

```bash
git clone https://github.com/Shreehari17/Intelligent-Research-Agent.git
cd Intelligent-Research-Agent
```

> The repository was originally named `Intelligent-Research-Agent`; the project-facing name is now **PayPilot — Agentic Payment Recovery**.

---

## 3. Create the virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Configure environment variables

Create `.env`:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password

# Optional — LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=paypilot-agentic-payment-recovery
```

---

## 6. Start PayPilot

```bash
python -m agent.graph
```

Then try:

```text
My payment success rate dropped today. Investigate why and tell me what I should do.
```

---

# 🌐 Run as an API

```bash
uvicorn main:app --reload --port 8001
```

Test:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "merchant-demo-1",
    "message": "My payment success rate dropped today. Investigate why and tell me what I should do."
  }'
```

Interactive API docs:

```text
http://localhost:8001/docs
```

---

## 🐳 Docker

The PayPilot agent includes Docker configuration:

```bash
docker-compose up --build
```

**The Multitenant-RAG service remains a separate dependency.**

When PayPilot and RAG run in separate containers, `localhost:8000` inside the PayPilot container will not refer to the RAG container. Configure the RAG host using the appropriate Docker-accessible hostname/service name.

---

## 🔐 Safety & Scope

PayPilot currently:

- analyzes synthetic payment data,
- retrieves internal recovery guidance,
- recommends recovery actions,
- records an audit event,
- exposes agent/tool traces through LangSmith.

It does **not**:

- move money,
- issue real refunds,
- modify real payment routing,
- access Razorpay production transactions,
- execute financial actions,
- or claim that revenue was actually recovered.

---

## 🎬 Recommended Demo

Use:

```text
My payment success rate dropped today. Investigate why and tell me what I should do.
```

Show three things:

### 1. Agent response

```text
Overall success rate: 86.3%
Yesterday: 91.4%

UPI:
66.7% today
90.7% yesterday

Timeout:
19 transactions
46.3% of today's failures
```

### 2. LangSmith trace

```text
agent
 ├── get_payment_analytics
 ├── get_payment_recovery_guidance
 └── final response
```

### 3. Audit record

```json
{
  "tools_used": [
    "get_payment_analytics",
    "get_payment_recovery_guidance"
  ],
  "recovery_executed": false
}
```

This demonstrates:

**Investigation → Diagnosis → Grounded Guidance → Recommendation → Audit**

---

## 🛣️ Future Improvements

- Razorpay/payment-gateway sandbox integration
- Mock recovery execution with explicit merchant approval
- Real-time payment monitoring
- Configurable merchant datasets
- Structured incident storage
- Streaming responses
- API authentication
- Production-grade audit storage
- Configurable recovery policies
- Automated alerting

---

## 🔗 Related Project

**Multitenant-RAG** is the separate retrieval service used by PayPilot:

```text
https://github.com/Shreehari17/Multitenant-RAG
```

PayPilot does not duplicate the retrieval pipeline. It consumes the RAG service through its HTTP retrieval endpoint.

---

## 👤 Author

**Shreehari**

GitHub:

```text
https://github.com/Shreehari17
```

---

## 📌 Project Summary

**PayPilot — Agentic Payment Recovery** demonstrates how an LLM can move beyond text generation into an evidence-driven operational workflow:

> **Detect payment degradation → diagnose the failure → retrieve domain-specific recovery guidance → recommend a bounded action → record the investigation.**

**Built with:** LangGraph · Groq · FastAPI · PostgreSQL · pgvector · RAG · Tavily · LangSmith · Docker
