<![CDATA[<div align="center">

# 🧠 AI-Enhanced DevOps Assistant

### _Autonomous, Closed-Loop Site Reliability Engineering with LLM-Driven Decision Making_

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a67d?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Telemetry-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?style=for-the-badge&logo=grafana&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.3-f55036?style=for-the-badge)
![SQLite](https://img.shields.io/badge/Audit_Log-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Alertmanager](https://img.shields.io/badge/Alertmanager-Webhooks-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<br/>

> **An AI SRE agent that watches your containers, thinks like an engineer, and acts like one too.**
>
> No human in the loop. No manual kubectl. No 3 AM pages.
> Just an LLM backed by a deterministic safety engine that auto-scales, auto-heals,
> and auto-restarts your infrastructure — then writes down why it did it.

<br/>

[Architecture](#-system-architecture) · [How It Works](#-the-autonomous-sre-pipeline) · [Safety Engine](#-the-deterministic-safety-engine) · [Setup](#-local-setup) · [Chaos Tests](#-chaos-engineering-suite) · [API](#-api-endpoints) · [Project Structure](#-project-structure)

</div>

---

## 📌 What This Project Does

Traditional DevOps monitoring tools **detect** problems and send alerts to humans. This project goes further — it **detects, diagnoses, decides, and acts** autonomously, in a closed feedback loop:

```
Problem Detected → AI Diagnoses Root Cause → Safety Engine Validates → Infrastructure Mutated → Audit Logged
```

| Capability | How It Works |
|---|---|
| **Auto-Scaling** | Detects CPU saturation via Prometheus → LLM recommends `scale_up` → Action Engine runs `docker compose up --scale app=N` → Nginx config rewritten & hot-reloaded with zero downtime |
| **Auto-Healing** | Detects HTTP 5xx error cascades or memory leaks → LLM recommends `restart_container` → Action Engine performs rolling container restarts |
| **Auto-Downscaling** | Detects idle over-provisioned replicas (CPU < 20%) → LLM recommends `scale_down` → Fleet shrinks to save resources |
| **Emergency Override** | If all containers die (0 replicas), the Safety Engine **bypasses the LLM entirely** and forces an immediate cold-boot resurrection |
| **Interactive Chat** | Developers can ask the AI questions about cluster health via a `/chat` endpoint — it responds with live telemetry analysis and can trigger actions |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE STACK                            │
│                                                                        │
│  ┌──────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────────┐  │
│  │  Target   │   │              │   │            │   │   Grafana    │  │
│  │  Flask    │◄──│    Nginx     │   │ Prometheus │   │  Dashboard   │  │
│  │  App x N  │   │  (LB:80)    │   │  (:9090)   │   │   (:3000)   │  │
│  │  (:5000)  │──►│              │   │            │   │              │  │
│  └────┬──────┘   └──────────────┘   └─────┬──────┘   └──────────────┘  │
│       │ /metrics                   scrapes │every 5s                    │
│       │◄──────────────────────────────────┘                            │
│       │                            fires if                            │
│       │                          breach sustained                      │
│       │                       ┌──────────────┐                         │
│       │                       │ Alertmanager │                         │
│       │                       │   (:9093)    │                         │
│       │                       └──────┬───────┘                         │
│       │                              │ POST /webhook                   │
│       │         ┌────────────────────▼──────────────────────┐          │
│       │         │          SENTINEL API (:8000)              │          │
│       │         │  ┌──────────────────────────────────────┐  │          │
│       │         │  │ Context     │ LLM Client │ Safety   │  │          │
│       │         │  │ Builder     │ (Groq API) │ Engine   │  │          │
│       │         │  │ (PromQL)    │ Llama 3.3  │ (Rules)  │  │          │
│       │         │  └──────────────────────────────────────┘  │          │
│       │         │  ┌──────────────────────────────────────┐  │          │
│       │         │  │ Action Engine │ Memory  │ Scheduler │  │          │
│       │         │  │ (Docker SDK)  │(SQLite) │  (CRON)   │  │          │
│       │         │  └──────────────────────────────────────┘  │          │
│       │◄────────│  docker.sock + compose scale + nginx write │          │
│                 └────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Tech | Role |
|---|---|---|
| **Target App** | Flask + `prometheus_flask_exporter` | The application being monitored. Dynamically scaled 1–5 replicas. Exposes `/metrics` for Prometheus and `/chaos/*` endpoints for testing |
| **Nginx** | `nginx:alpine` | Layer 7 reverse proxy. Config is **rewritten programmatically** by the Action Engine on every scale event, then hot-reloaded (`nginx -s reload`) for zero-downtime traffic redistribution |
| **Prometheus** | `prom/prometheus` | Scrapes container metrics every 5s via `docker_sd_configs` (auto-discovers new replicas). Evaluates alert rules and forwards breaches to Alertmanager |
| **Alertmanager** | `prom/alertmanager` | Waits for sustained threshold breaches (via `for:` durations), then fires a webhook `POST` to the Sentinel API |
| **Grafana** | `grafana/grafana` | Pre-provisioned dashboard showing CPU, Memory, Error Rate, Request Rate, and Replica Count in real-time |
| **Sentinel API** | FastAPI + Uvicorn (Python 3.11) | The brain. Runs the CRON scheduler, receives webhooks, hosts the chat endpoint, orchestrates the full decision pipeline |
| **SQLite** | `memory.db` (host bind-mount) | Persistent audit log. Survives container teardowns. Stores every incident, AI reasoning, action taken, and execution status |

---

## 🔄 The Autonomous SRE Pipeline

Every decision — whether triggered by a CRON tick or an Alertmanager webhook — flows through the same 7-stage pipeline:

```
TRIGGER
  │  (CRON every 60s)  OR  (Alertmanager Webhook)  OR  (Developer /chat)
  │
  ▼
STAGE 1 ─── Telemetry Harvest (context_builder.py)
  │          Fires 6 PromQL queries against Prometheus:
  │            • avg(rate(process_cpu_seconds_total[15s])) * 100
  │            • sum(process_resident_memory_bytes) / 1024 / 1024
  │            • HTTP 5xx error rate %
  │            • Request rate per second
  │            • count(up{job="target_app"} == 1)  →  active replicas
  │            • count(ALERTS{alertstate=~"pending|firing"})
  │
  ▼
STAGE 2 ─── Memory Retrieval (memory.py)
  │          Fetches the last 5 actions from SQLite to prevent
  │          "Goldfish Loops" (repeating the same action endlessly)
  │
  ▼
STAGE 3 ─── LLM Synthesis (llm_client.py + prompts.py)
  │          Sends system_state + history to Groq Cloud (Llama 3.3 70B)
  │          with a structured SRE system prompt. Returns:
  │          { action, reason, confidence }
  │
  ▼
STAGE 4 ─── Deterministic Safety Engine (safety_engine.py)
  │          6 hardcoded rule layers validate the LLM's output.
  │          Can REJECT or OVERRIDE the LLM. (See detailed breakdown below)
  │
  ▼
STAGE 5 ─── Daemon Execution (action_engine.py)
  │          Talks to Docker Engine via Unix socket:
  │            • scale_up/down  →  docker compose up --scale app=N
  │            • restart        →  container.restart() per replica
  │
  ▼
STAGE 6 ─── Traffic Routing (action_engine.py)
  │          Rewrites /etc/nginx/nginx.conf with updated upstream
  │          servers, then executes nginx -s reload (zero downtime)
  │
  ▼
STAGE 7 ─── Audit Commit (memory.py)
             Writes incident context, AI reasoning, action, and
             execution status to SQLite. Persists across restarts.
```

---

## 🛡 The Deterministic Safety Engine

> The LLM proposes. The Safety Engine disposes.

This is the project's core innovation. The Safety Engine (`safety_engine.py`) is a **308-line, pure-Python rules engine** that sits between the LLM and the infrastructure. It contains zero ML — just deterministic `if/else` logic that an LLM cannot talk its way around.

### Rule Cascade (executed in order)

Every decision passes through these 6 rules **sequentially**. The first rule that triggers short-circuits the rest:

| # | Rule | What It Does | Example |
|---|---|---|---|
| **0** | **Defibrillator** | If `active_replicas < 1` for 15s, **bypasses the LLM entirely** and forces `scale_up` | All containers crashed → emergency resurrection |
| **1** | Structural Validation | Rejects if the LLM output isn't `{action, reason, confidence}` or action isn't in the 4 allowed values | LLM hallucinated `"action": "deploy_hotfix"` → rejected |
| **2** | Confidence Gate | Rejects if `confidence < 0.6` | LLM unsure (`confidence: 0.4`) → forced `no_action` |
| **3** | Replica Bounds | Prevents scaling below 1 or above 5 replicas | Already at 5 replicas → `scale_up` rejected |
| **4** | Metrics Sanity Check | Cross-validates the action against actual numbers. Includes a **Memory Leak Hard Override** that forces `restart_container` when memory is high but CPU/errors are low | LLM says `no_action` but memory is at 200MB with 3% CPU → Safety Engine overrides to `restart_container` |
| **5** | Sustained Breach Gate | For CRON-triggered decisions, requires the metric breach to persist for the same duration as `alert_rules.yml`'s `for:` field. Prevents CRON from racing Alertmanager | CPU spiked for 5s → too short, rejected (must sustain 15s) |
| **6** | Cooldown | Enforces a **120-second cooldown** between any infrastructure-mutating actions | Scaled up 30s ago → next action rejected until cooldown expires |

### Why This Matters

LLMs are probabilistic — they can hallucinate, contradict themselves, or make overconfident bad calls. The Safety Engine ensures:

- ✅ **No runaway scaling** (bounded 1–5 replicas)
- ✅ **No action spam** (120s cooldown between mutations)
- ✅ **No false positives** (sustained-breach gates mirror Prometheus alert rules)
- ✅ **No missed emergencies** (Rule 0 bypasses everything when fleet is dead)
- ✅ **LLM-proof memory leak detection** (hard override even if LLM says "no_action")

---

## 🧪 Chaos Engineering Suite

The repository includes purpose-built stress tests that simulate real production failures and trigger the autonomous pipeline end-to-end.

### Scenario A: CPU Saturation (Viral Traffic Surge)

```bash
python3 tests/cpu_test.py
```

**What it does:** Hits the `/chaos/cpu` endpoint, which spawns multiple CPU-bound threads (2× core count) that burn at near-100% for 5 minutes.

**Expected autonomous response:**
```
Prometheus detects avg(CPU) > 75%
  → Alert fires after 15s sustained breach
    → Alertmanager sends POST /webhook to Sentinel API
      → LLM analyzes metrics + history → outputs { action: "scale_up", confidence: 0.92 }
        → Safety Engine validates (breach sustained ✓, cooldown clear ✓, replicas < 5 ✓)
          → Action Engine: docker compose up --scale app=2
            → Nginx config rewritten with 2 upstream servers → hot-reload
              → SQLite logs: "scale_up | executed"
```

**Grafana observation:** CPU drops as load distributes across new replicas while stress is still active.

---

### Scenario B: HTTP 5xx Error Cascade

```bash
python3 tests/sys_error_test.py
```

**What it does:** Floods the app with requests to `/chaos/error`, which returns HTTP 500.

**Expected autonomous response:**
```
Prometheus detects error_rate > 5%
  → HighErrorRate alert fires after 1m sustained
    → LLM diagnoses state corruption → outputs { action: "restart_container" }
      → Safety Engine approves → Action Engine restarts all app containers
        → Error rate drops to 0% → SQLite logs the incident
```

---

### Scenario C: Memory Leak

```bash
python3 tests/mem_test.py
```

**What it does:** Repeatedly hits `/chaos/memory`, which appends 50MB of junk data per request into a global Python list (simulating a leak).

**Expected autonomous response:**
```
Memory climbs past 150MB while CPU stays low
  → HighMemoryUsage alert fires after 1m sustained
    → LLM may say "no_action" (common LLM failure mode for leaks)
      → Safety Engine OVERRIDES LLM → forces restart_container
        → Containers restart → leaked memory reclaimed → SQLite logs the override
```

> **Note:** This scenario specifically demonstrates the Safety Engine's Memory Leak Hard Override (Rule 4b) — even when the LLM makes the wrong call, the deterministic rules catch it.

---

### Scenario D: Combined Stress

```bash
python3 tests/combined_load_test.py
```

Fires CPU + Memory + Error chaos simultaneously to test the pipeline under compound failure conditions.

---

## 🚀 Local Setup

### Prerequisites

| Requirement | Why |
|---|---|
| **Docker Desktop** | The entire stack runs as Docker Compose services. Enable WSL2 integration on Windows |
| **Python 3.11+** | Only needed on the host to run chaos test scripts |
| **Groq API Key** | Free at [console.groq.com](https://console.groq.com). Powers the LLM (Llama 3.3 70B) |

### Step 1: Configure Environment

```bash
# Create a .env file in the project root
echo 'GROQ_API_KEY="gsk_your_key_here"' > .env
```

### Step 2: Launch the Stack

```bash
docker compose up --build -d
```

This provisions **6 containers** in one command:

| Container | Port | URL |
|---|---|---|
| `app` (Target Flask App) | 5000 (internal) | Accessed via Nginx |
| `nginx` (Load Balancer) | **80** | [http://localhost](http://localhost) |
| `prometheus` | **9090** | [http://localhost:9090](http://localhost:9090) |
| `alertmanager` | **9093** | [http://localhost:9093](http://localhost:9093) |
| `grafana` | **3000** | [http://localhost:3000](http://localhost:3000) (admin/admin) |
| `sentinel_api` (The Brain) | **8000** | [http://localhost:8000](http://localhost:8000) |

### Step 3: Verify

```bash
docker ps                                          # All 6 containers running
docker compose logs -f sentinel_api                # Watch the AI think in real-time
curl http://localhost:8000/                         # "THE CORE API SERVER RUNNING SUCCESSFULLY!"
```

### Step 4: Trigger Chaos & Watch

```bash
# In terminal 1: Watch the AI's decision log
docker compose logs -f sentinel_api

# In terminal 2: Trigger a CPU surge
python3 tests/cpu_test.py

# In browser: Open Grafana at localhost:3000 to see metrics respond in real-time
```

---

## 🌐 API Endpoints

| Method | Endpoint | Trigger | Description |
|---|---|---|---|
| `GET` | `/` | Manual | Health check |
| `POST` | `/webhook` | Alertmanager | Receives firing alerts, runs the full 7-stage pipeline autonomously |
| `POST` | `/chat` | Developer | `{ "message": "Why is memory so high?" }` — LLM responds with telemetry-grounded diagnosis |
| `POST` | `/execute` | UI / Manual | `{ "action": "scale_up" }` — Bypass the LLM, execute a manual infrastructure action directly |

---

## 📁 Project Structure

```
AI-Enhanced-DevOps-Assistant/
│
├── docker-compose.yml              # Master orchestration — all 6 services
├── .env                            # GROQ_API_KEY (gitignored)
│
├── src/                            # ── THE SENTINEL AI BRAIN ──
│   ├── main.py                     # FastAPI entrypoint + lifespan scheduler
│   ├── Dockerfile                  # Python 3.11 + Docker CLI + Compose plugin
│   ├── requirements.txt            # groq, fastapi, uvicorn, docker, httpx, apscheduler, rich
│   │
│   ├── api/                        # Request handling & orchestration
│   │   ├── routes.py               # /webhook, /chat, /execute endpoints
│   │   ├── context_builder.py      # PromQL queries → system_state dict
│   │   ├── scheduler.py            # APScheduler CRON (1-min interval health checks)
│   │   ├── mutation_lock.py        # threading.Lock to serialize CRON vs webhook
│   │   └── log_formatter.py        # Rich-powered color-coded terminal logging
│   │
│   ├── brain/                      # AI decision-making
│   │   ├── llm_client.py           # Async Groq SDK client (Llama 3.3 70B, temp=0.2)
│   │   ├── prompts.py              # System prompt + incident prompt builder
│   │   └── safety_engine.py        # 6-layer deterministic validation rules
│   │
│   └── executor/                   # Infrastructure mutation
│       ├── action_engine.py        # Docker SDK: scale, restart, nginx rewrite
│       ├── memory.py               # SQLite CRUD (init, save, query)
│       └── service.py              # Decision → audit log serializer
│
├── target_app/                     # ── THE MONITORED APPLICATION ──
│   ├── app.py                      # Flask app with /chaos/cpu, /chaos/memory, /chaos/error
│   ├── Dockerfile                  # Python 3.11 slim
│   └── requirements.txt            # flask, prometheus-flask-exporter
│
├── infra/                          # ── INFRASTRUCTURE CONFIGS ──
│   ├── prometheus/
│   │   ├── prometheus.yml          # docker_sd_configs auto-discovery, 5s scrape
│   │   └── alert_rules.yml         # HighCPU (>75%, 15s), HighMemory (>150MB, 1m), HighErrors (>5%, 1m)
│   ├── alertmanager/
│   │   └── alertmanager.yml        # Webhook → http://sentinel_api:8000/webhook
│   ├── nginx/
│   │   ├── nginx.conf              # Live config (rewritten by Action Engine, gitignored)
│   │   └── nginx.conf.default      # Reset template (applied on every container startup)
│   └── grafana/
│       ├── dashboards/             # Pre-provisioned Sentinel dashboard JSON
│       └── provisioning/           # Auto-configured datasource + dashboard provider
│
└── tests/                          # ── CHAOS ENGINEERING ──
    ├── cpu_test.py                 # Viral traffic surge simulation
    ├── mem_test.py                 # Memory leak simulation
    ├── sys_error_test.py           # HTTP 500 cascade simulation
    ├── combined_load_test.py       # Multi-vector compound failure
    └── nodes_test.py               # Node-level stress test
```

---

## 🔑 Key Design Decisions

### Why a Safety Engine instead of just trusting the LLM?

LLMs are probabilistic. In testing, we observed Llama 3.3 occasionally:
- Saying `"no_action"` during active memory leaks (leaks don't look "broken" to an LLM)
- Recommending `"scale_up"` for memory leaks (adding replicas that will also leak)
- Ignoring its own cooldown instructions from the system prompt

The Safety Engine is the deterministic backstop that makes this system **production-grade**, not just a demo.

### Why Docker socket mounting instead of Kubernetes?

This project targets **local Docker Compose environments** for demonstrability. The Sentinel API container mounts:
- `/var/run/docker.sock` — to query and control the Docker daemon
- `/project_root` — to run `docker compose up --scale`
- `/etc/nginx_shared` — to rewrite and reload the load balancer

### Why SQLite instead of Postgres?

Zero configuration. The `memory.db` file is bind-mounted to the host, so audit logs **survive container teardowns**. For a local demo system, this is the right trade-off: no network overhead, no connection pooling, no setup.

### Why Groq + Llama 3.3?

Groq's inference speed (~200 tokens/s) ensures the decision pipeline completes in <2 seconds. Combined with `temperature=0.2` for consistency and `response_format=json_object` for structured output, we get fast, reliable SRE decisions.

---

## 📊 Inspecting the AI's Memory

The SQLite audit log (`memory.db`) persists on the host via a Docker bind mount. Query it directly:

```bash
# View the decision timeline
sqlite3 src/memory.db "SELECT timestamp, action, status FROM action_logs ORDER BY id DESC LIMIT 10;"

# Read the AI's exact reasoning for the latest incident
sqlite3 src/memory.db "SELECT reasoning, incident FROM action_logs ORDER BY id DESC LIMIT 1;"

# Count how many times each action was taken
sqlite3 src/memory.db "SELECT action, COUNT(*) as count FROM action_logs GROUP BY action ORDER BY count DESC;"
```

---

## ⚙️ Configuration Reference

| Parameter | File | Default | Purpose |
|---|---|---|---|
| `CONFIDENCE_THRESHOLD` | `safety_engine.py` | `0.6` | Minimum LLM confidence to execute an action |
| `COOLDOWN_SECONDS` | `safety_engine.py` | `120` | Mandatory wait between infrastructure mutations |
| `MIN_REPLICAS` / `MAX_REPLICAS` | `safety_engine.py` | `1` / `5` | Hard scaling bounds |
| `HIGH_CPU_THRESHOLD` | `safety_engine.py` | `70%` | CPU above this → scale_up considered valid |
| `HIGH_MEMORY_THRESHOLD` | `safety_engine.py` | `150 MB` | Memory above this → leak detection activates |
| `HIGH_ERROR_RATE_THRESHOLD` | `safety_engine.py` | `5%` | Error rate above this → restart considered valid |
| `EXTINCTION_CONFIRM_SECONDS` | `safety_engine.py` | `15` | How long 0-replica state must persist before emergency boot |
| `scrape_interval` | `prometheus.yml` | `5s` | How often Prometheus scrapes container metrics |
| `CPU_SPIKE_DURATION_SECONDS` | `target_app/app.py` | `300s` | How long the chaos CPU test burns |
| `MODEL_NAME` | `llm_client.py` | `llama-3.3-70b-versatile` | The LLM model used for decisions |
| CRON interval | `scheduler.py` | `60s` | Background health check frequency |

---

## 📜 License

MIT License — Copyright (c) 2026 **Alvin George**

See [LICENSE](LICENSE) for full text.
]]>
