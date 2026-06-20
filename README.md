# 🤖 AI-Assisted DevOps Engine & Auto-SRE Copilot

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a67d?style=flat&logo=fastapi) ![Flask](https://img.shields.io/badge/Target_Fleet-Flask-000000?style=flat&logo=flask) ![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker) ![Prometheus](https://img.shields.io/badge/Prometheus-Telemetry-E6522C?style=flat&logo=prometheus) ![Groq](https://img.shields.io/badge/LLM-Groq_Cloud-f55036?style=flat) ![SQLite](https://img.shields.io/badge/Audit_Store-SQLite3-003B57?style=flat&logo=sqlite)![AlertManager](https://img.shields.io/badge/alertmanager-Telemetry-E6522C?style=flat&logo=alertmanager)

An autonomous, closed-loop Site Reliability Engineering (SRE) platform. The system continuously ingests container telemetry, evaluates cluster health via a large language model, passes decisions through a deterministic Python safety guardrail, and executes zero-downtime infrastructure mutations (auto-scaling and auto-healing) directly against the local Docker Engine daemon.

---

## System Architecture

```text
Target Fleet : Flask ('DPC' dynamically scaled Compose replicas, port 5000)
Telemetry    : Prometheus (docker_sd_configs) ➔ Alertmanager (port 9093)
Edge Proxy   : Nginx Alpine (Dynamic upstream mapping, zero-downtime reloads)
Framework    : FastAPI / Python 3.11 (Async Uvicorn engine, port 8000)
The Brain    : Groq Cloud LLM + Deterministic Safety Engine (Confidence >= 0.6)
Audit Store  : Serverless SQLite3 (Immortal host bind-mount, ./src/memory.db)

```

---

## The Autonomous SRE Pipeline

```text
CRON TICK (Every 3m) OR ALERTMANAGER WEBHOOK TRIGGER
  │
  ├─► 1. Telemetry Harvest : ContextBuilder queries PromQL (avg CPU, RAM sum, 5xx rate)
  ├─► 2. Memory Retrieval  : SQLite fetches last 3 actions to prevent Dory/Goldfish loops
  ├─► 3. LLM Synthesis     : Groq diagnoses fleet state against strict prompt constraints
  ├─► 4. Safety Guardrail  : Validates JSON bounds, confidence threshold, and metric sanity
  ├─► 5. Daemon Execution  : Invokes Unix socket to run `compose up --scale` or `restart`
  ├─► 6. Traffic Routing   : Rewrites /etc/nginx/nginx.conf & fires `nginx -s reload`
  └─► 7. State Audit       : Commits incident context, AI reasoning, and status to SQLite

```

---

## Local Setup

### 1. Prerequisites

* **Docker Desktop** (Ensure WSL2 integration is enabled if running on Windows).
* **Python 3.11+**
* **Groq API Key** (`gsk_...`)

### 2. Environment Configuration

Create a `.env` file in the project root directory:

```bash
GROQ_API_KEY="gsk_your_groq_api_key_here"

```

### 3. Boot the Infrastructure Engine

Deploy the master Compose stack. This will provision the load balancer, the Prometheus monitoring engine, the AI Copilot API, and 1 initial replica of the `DPC` target application.

```bash
docker compose up --build -d

```

Verify the active fleet:

```bash
docker ps

```

---

## Chaos Engineering Suite

The repository includes deterministic test scripts to artificially simulate catastrophic production failures and trigger the autonomous DevOps copilot.

### Scenario A: Viral Traffic Surge (CPU Saturation)

Locks application threads in infinite factorial loops to simulate a massive traffic spike.

```bash
python3 tests/cpu_test.py

```

* **Expected SRE Behavior:** Prometheus detects `avg(CPU) > 80%`. Alertmanager fires a Webhook. The AI Brain commands `scale_up`. The Action Engine scales the `DPC` container fleet from `1 ➔ 2` replicas and seamlessly reloads Nginx.

### Scenario B: Cascading Database Failures (HTTP 500 Cascade)

Floods the edge proxy with rapid-fire fatal server errors.

```bash
python3 tests/sys_error_test.py

```

* **Expected SRE Behavior:** Telemetry detects a 5xx HTTP error rate exceeding the `5%` cluster threshold. The AI Brain diagnoses a corrupted application state and commands `restart_container`. The Action Engine executes a rolling reboot of the `DPC` containers.

---

## Inspecting the Memory

Because the local SQLite database (`memory.db`) is bound directly to the host storage via a two-way Docker bind mount, audit logs permanently survive container teardowns.

To interrogate the AI's historical decision-making timeline from your host terminal:

```bash
sqlite3 src/memory.db "SELECT timestamp, action, status FROM action_logs;"

```

To view the raw Prometheus metric payloads and the LLM's exact internal reasoning for a specific incident:

```bash
sqlite3 src/memory.db "SELECT reasoning, incident FROM action_logs ORDER BY id DESC LIMIT 1;"

```