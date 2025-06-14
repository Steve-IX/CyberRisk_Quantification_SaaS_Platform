# Risk-Analytics SaaS Platform - Product Specification

**Version:** 1.0  
**Target:** UK-EU Mid-Market Companies (NIS2 & CSRD Compliance)  
**Core:** Cyber-Risk Quantification (CRQ) via Monte Carlo Simulation

---

## 1  Essence & Core Value

| Pillar                            | What the product *really* does                                                                                              | Why buyers hand over budget                                                           |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Translate tech risk → £££**     | Runs FAIR-style¹ simulations and shows "expected loss", P-percentiles and control ROI in *currency* rather than RAG charts. | Boards, insurers and auditors now demand hard numbers.                                |
| **Automate compliance artifacts** | Spits out CSRD "cyber-risk disclosure" & NIS2 risk-treatment annexes straight from the simulation results.                  | Saves dozens of analyst hours each quarter. ([dart.deloitte.com][1], [puppet.com][2]) |
| **Optimise controls**             | Linear / integer optimiser tells you which mitigations hit a loss-exposure target at minimum cost.                          | Lets CISOs defend spend in budget talks.                                              |

¹ FAIR is the de-facto quantitative standard for cyber-risk ([fairinstitute.org][3], [fairinstitute.org][4])

---

## 2  Functional Stack (MVP → v2)

### 2.1 Data ingestion

| Source                                              | MVP | v2 |
| --------------------------------------------------- | --- | -- |
| Manually uploaded CSVs (assets, controls, events)   | ✔   | —  |
| Jira / ServiceNow export                            | —   | ✔  |
| Vulnerability scanners (OpenVAS, Tenable)           | —   | ✔  |
| Cloud asset APIs (AWS Config, Azure Resource Graph) | —   | ✔  |

### 2.2 Risk engine

1. **Scenario builder** – user selects *threat event ↔ asset ↔ control list*.
2. **Monte-Carlo simulator** (already in your repo):
   * **Distribution definitions**: loss magnitude (log-normal), frequency (Poisson), control efficacy (beta).
   * **10 k+ iterations** – vectorised NumPy; optional GPU (CuPy) toggle for >1 m runs.
3. **Optimizer** (existing `control_optimizer.py`):
   * Objective: minimise *Annualised Loss Expectancy* under a budget or risk-appetite constraint.
   * Solver: SciPy `linprog` (MVP) → switch to OR-Tools or Pyomo for integer budgets later.
4. **Report generator**: JSON → PDF (WeasyPrint) including graphs & executive summary.

### 2.3 API surface

| Route               | Verb | Body                     | Returns                      |
| ------------------- | ---- | ------------------------ | ---------------------------- |
| `/simulate`         | POST | scenarios\[], iterations | run\_id                      |
| `/results/{run_id}` | GET  | —                        | percentiles, histograms, ALE |
| `/optimise`         | POST | controls\[], target      | control set, residual risk   |

OAuth2 bearer + PAT; rate-limited (Burst 10 r/s).

### 2.4 Front-end workflow

1. **On-boarding wizard** → paste assets & annual loss guess.
2. **"Run simulation" button** → progress bar (SSE/WebSocket).
3. **Dashboard** with:
   * Tornado plot (loss exceedance curve)
   * KPI tiles: *P50 annual loss*, *P95*, *budget v. expected saving*
4. **Control recommendations** table with ROI column.
5. **Download report** → PDF, CSV, CSRD Annex.

---

## 3  Tech Stack & Languages

| Layer                     | Language / Framework                                                  | Rationale                                                              |
| ------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Core simulation**       | **Python** (NumPy, SciPy, Pandas)                                     | Leverages your existing code; huge ecosystem for scientific computing. |
| **Performance hot-spots** | Optional **Rust** modules compiled with PyO3 or **Cython**            | 5-20× speed-ups for tight loops if you outgrow NumPy.                  |
| **API**                   | **FastAPI** (Python)                                                  | Async, OpenAPI docs out-of-the-box, Lambda-friendly.                   |
| **Background jobs**       | **AWS Lambda** or **Fargate** containers                              | Pay-per-execution; no servers to patch.                                |
| **Front-end**             | **TypeScript + Next.js 15 (React 19)**                                | Server actions → easy file uploads, good SEO for public pages.         |
| **Charts**                | server-side **Matplotlib › PNG** (MVP) → **Recharts** in browser (v2) | Quick to start; migrate later for interactivity.                       |
| **Data store**            | **PostgreSQL** (RDS Serverless v2)                                    | ACID, cheap scale-to-zero, JSONB for flexible scenario specs.          |
| **Auth**                  | **Clerk** or **Auth0** (OIDC) + GitHub SSO                            | Offload tricky edge-cases; free tier generous.                         |
| **Payments**              | **Stripe Billing**                                                    | Seats + usage metering.                                                |
| **Infra as Code**         | **Pulumi (TypeScript)** or **Terraform**                              | Repeatable prod + staging envs.                                        |
| **CI/CD**                 | **GitHub Actions**                                                    | Matrix tests (Py 3.10-3.12), security scans.                           |

> *Why not Go?* Rust/Cython plugs only where Python isn't fast enough; staying Python-first keeps iteration velocity and reuse of your current test-suite.

---

## 4  Security & Compliance Must-Haves

| Item                   | How / Tool                                                                                          |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| **ISO 27001 controls** | Map FastAPI middlewares & AWS config to Annex A; export SoA PDF for prospects.                      |
| **Threat modelling**   | STRIDE session per microservice; store diagrams in repo.                                            |
| **Static analysis**    | Bandit + Semgrep in CI.                                                                             |
| **SBOM**               | CycloneDX JSON auto-generated; attach to each Docker image.                                         |
| **Data retention**     | Allow org-admin to auto-purge runs after X days; default 180.                                       |
| **NIS2 / CSRD fields** | Pre-filled based on simulation outputs (loss in €); exported in final PDF. ([iss-corporate.com][5]) |

---

## 5  Observability & Ops

* **Logging:** JSON logs → AWS CloudWatch → Grafana Cloud.
* **Metrics:** Prom-style counters for sims/sec, p95 duration, £/Lambda run.
* **Tracing:** OpenTelemetry; tie front-end clicks to API latency.
* **Alerting:** PagerDuty for *error rate > 2 %* or *sim backlog > 100*.
* **Cost guard-rails:** AWS Budgets → Slack alert if spend > £50 this month (MVP).

---

## 6  Road-Mapped Differentiators

1. **Continuous CRQ** – nightly cron re-runs using latest vuln scan; plots trend line.
2. **Third-party risk lens** – import supplier list, weight loss-scenarios by vendor criticality (matches new EU supply-chain duty rules).
3. **Insurance integration** – push PDFs + raw JSON to CFC, Axa, Hiscox underwriting portals for instant premium quotes; take referral cut.
4. **Gen-AI narrative** – LLM turns the numbers into a board-ready one-pager ("£3.2 m expected loss reduced to £850 k if we fund these three controls").

---

## 7  Testing & Quality

| Layer       | Tests                                                                           |
| ----------- | ------------------------------------------------------------------------------- |
| Python core | PyTest unit + property-based (Hypothesis) to assert distribution outputs.       |
| API         | Schemathesis → fuzz OpenAPI schema.                                             |
| Front-end   | Playwright e2e; Axe-core for accessibility.                                     |
| Performance | Locust swarm with 1 k concurrent sims; verify p95 < 1 s for 10 k-iteration run. |
| Chaos       | AWS Fault-Injection start/stop Postgres; ensure queue retries.                  |

---

## 8  Team & Timeline Snapshot

| Week  | Deliverable                                          | Lead             |
| ----- | ---------------------------------------------------- | ---------------- |
| 1–2   | Package core lib + unit tests pass in CI             | You              |
| 3–4   | `/simulate` + `/results` FastAPI routes + PoC Lambda | Backend          |
| 5–6   | Next.js dashboard skeleton, auth stub                | Front-end        |
| 7     | Stripe checkout & seat gating                        | Full-stack       |
| 8     | PDF export + CSRD annex template                     | Backend          |
| 9     | Beta launch to 5 design-partners (£49/mo)            | PM / Growth      |
| 10–12 | Optimiser, control ROI view, first NIS2 mapping      | Backend + SecOps |

Small team of **2 devs + 0.5 designer** can hit first revenue inside 90 days.

---

## 9  Reference Architecture

```
Client (Next.js) ──HTTPS──► API Gateway
                       │
                       ▼
                 FastAPI (Lambda)
               /      |        \
  Auth (OIDC) ·   Sim Queue   · Optimiser Worker (Lambda↦Rust)
               \      |        /
                ▼     ▼       ▼
          Postgres  S3(Reports)  EventBridge
```

---

## 10  Go-to-Market Strategy

### 10.1 Ideal Customer Profile (ICP)
* **Size:** 50-500 employees
* **Sector:** Tech, professional services, healthcare (PII/cardholder data)
* **Pain:** CISO/vCISO struggles to justify security spend with hard numbers
* **Trigger:** NIS2 deadline (Oct 2024), CSRD reporting requirements

### 10.2 Pricing Strategy

| Tier        | Price/Month | Users | Simulations | Features                    |
|-------------|-------------|-------|-------------|----------------------------|
| **Starter** | £49         | 2     | 50          | Basic sims, CSV export     |
| **Pro**     | £199        | 10    | 500         | Optimiser, PDF reports     |
| **Enterprise** | £499     | 25    | Unlimited   | API access, white-label    |

**Usage-based add-ons:**
- Extra simulations: £0.10 each
- Premium support: £99/month
- Custom integrations: £1,999 setup

### 10.3 Launch Channels
1. **LinkedIn targeting:** "CISO UK & Ireland", "SME Cyber-Essentials" groups
2. **Speaking circuit:** Local OWASP/ISACA chapters
3. **Content marketing:** "NIS2 for SMEs: quantify, don't colour-code" blog series
4. **Partnership:** Cyber-Essentials assessors, vCISO consultancies

---

## 11  Additional Specifications

### 11.1 Database Schema (PostgreSQL)

```sql
-- Core entities
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE,
    role VARCHAR(50), -- admin, analyst, viewer
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    name VARCHAR(255),
    category VARCHAR(100), -- server, database, application
    value_gbp DECIMAL(12,2),
    criticality INTEGER CHECK (criticality BETWEEN 1 AND 5)
);

CREATE TABLE scenarios (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    name VARCHAR(255),
    threat_event VARCHAR(255),
    affected_assets UUID[], -- array of asset IDs
    frequency_params JSONB, -- Poisson parameters
    impact_params JSONB,    -- Log-normal parameters
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY,
    scenario_id UUID REFERENCES scenarios(id),
    iterations INTEGER,
    status VARCHAR(50), -- pending, running, completed, failed
    results JSONB, -- percentiles, ALE, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### 11.2 API Specifications (OpenAPI)

```yaml
openapi: 3.0.0
info:
  title: CyberRisk Quantification API
  version: 1.0.0
paths:
  /api/v1/simulate:
    post:
      summary: Start simulation
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                scenario_id:
                  type: string
                  format: uuid
                iterations:
                  type: integer
                  minimum: 1000
                  maximum: 1000000
      responses:
        '202':
          description: Simulation queued
          content:
            application/json:
              schema:
                type: object
                properties:
                  run_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: [pending]
```

### 11.3 Compliance Mappings

#### NIS2 Article 21 Requirements
- **Risk management measures** → Simulation scenarios
- **Business continuity** → Impact calculations
- **Supply chain security** → Third-party risk lens (v2)
- **Incident handling** → Post-incident loss analysis

#### CSRD Disclosure Requirements
- **Cyber risks materiality** → ALE vs revenue percentage
- **Risk mitigation measures** → Control effectiveness analysis
- **Financial impact** → Monte Carlo loss distributions

---

## 12  Implementation Roadmap

### Phase 1: Core Engine (Weeks 1-4)
1. Refactor existing Python modules into reusable library
2. Create FastAPI wrapper with `/simulate` endpoint
3. PostgreSQL schema + basic CRUD operations
4. Docker containerization

### Phase 2: MVP SaaS (Weeks 5-8)
1. Next.js dashboard with auth
2. File upload for assets/scenarios
3. Real-time simulation progress
4. Basic PDF report generation

### Phase 3: Market Ready (Weeks 9-12)
1. Stripe integration + subscription tiers
2. Control optimization UI
3. CSRD/NIS2 report templates
4. Performance optimization

---

## Take-away

*Keep the promise razor-thin:* **"Click-upload-simulate → get a £ figure your board understands."** Nail that flow; the optimizations, scanners and fancy AI write-ups can come later. With Python + FastAPI for brains, Next.js for face, and AWS serverless for muscle, you can ship fast, stay cheap, and iterate weekly—exactly what early-paying customers reward.

Now crack open the repo, rename it `cyberrisk_core`, and stub the `/simulate` Lambda—you're already halfway there. 🚀

[1]: https://dart.deloitte.com/USDART/home/publications/deloitte/heads-up/2023/csrd-corporate-sustainability-reporting-directive-faqs
[2]: https://www.puppet.com/blog/nis2
[3]: https://www.fairinstitute.org/what-is-fair
[4]: https://www.fairinstitute.org/
[5]: https://www.iss-corporate.com/library/eu-omnibus-update-parliament-hearing-shines-light-on-process-deficiencies/ 