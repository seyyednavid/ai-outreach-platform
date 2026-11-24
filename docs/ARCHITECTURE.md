# Architecture

This document describes the system as it is implemented in this repository. Three diagrams cover the runtime architecture, the agent workflow and the delivery pipeline. They are written in Mermaid, so GitHub renders them directly and they can be edited as text.

- [Runtime architecture](#runtime-architecture)
- [Agent workflow](#agent-workflow)
- [Delivery pipeline](#delivery-pipeline)
- [Components](#components)
- [Design decisions](#design-decisions)

## Runtime architecture

```mermaid
flowchart TB
    user(["User's browser"])

    subgraph run["Google Cloud Run · London (europe-west2)"]
        direction LR
        fe["Frontend<br/>React + Vite on nginx"]
        be["Backend API<br/>FastAPI + OpenAI Agents SDK"]
        job["Migration job<br/>Alembic, started by hand"]
    end

    subgraph gcp["Google Cloud services"]
        direction LR
        sm[("Secret Manager")]
        obs["Cloud Logging<br/>Cloud Monitoring"]
    end

    subgraph supa["Supabase · London"]
        direction LR
        auth["Auth"]
        db[("PostgreSQL 17")]
    end

    subgraph ext["External APIs"]
        direction LR
        openai["OpenAI<br/>agents · web search · traces"]
        gmail["Google OAuth<br/>Gmail API: drafts only"]
    end

    user -->|"loads the app"| fe
    user -->|"signs in"| auth
    user -->|"REST + JWT"| be
    be -->|"verifies JWT"| auth
    be --> db
    job --> db
    be --> openai
    be --> gmail
    sm -.->|"secrets"| be
    be -.->|"JSON logs · health checks"| obs
```

The browser talks to three things: the static frontend, Supabase Auth (sign in) and the backend API, sending the Supabase access token as a Bearer token. Only the backend talks to the database, OpenAI and Gmail.

## Agent workflow

```mermaid
flowchart TD
    U["User picks a lead, and optionally a product and a contact"] --> CTX["Backend builds the context from PostgreSQL<br/>catalogue facts · contact name only"]
    CTX --> R["Research agent<br/>web search · sourced findings"]
    R --> W["Writer agent"]
    W --> F["Code: add the signature,<br/>keep one call to action"]
    F --> V["Reviewer agent<br/>scores · flagged claims with quotes"]
    V --> C{"Code checks<br/>score ≥ 8 · flag quotes exist in the email<br/>no placeholders · no flags left"}
    C -- "fails, at most 2 times" --> I["Improver agent"]
    I --> F
    C -- "passes, or limit reached" --> S[("Run saved with a snapshot<br/>of the context, trace id, tokens and cost")]
    S --> H["Human: edit · ask the AI to re-check · approve<br/>approving a failed draft needs an explicit override"]
    H --> G["Gmail draft in the user's mailbox<br/>never sent automatically"]
```

Two more agents run before this flow, when the user asks for them on the New draft page:

- **Solution matching agent:** recommends one product from the seller's catalogue. The backend rejects any product id that is not in that catalogue.
- **Contact discovery agent:** runs three focused web searches in parallel (leadership pages, appointment news, trade press). Python then merges, de-duplicates, ranks and source-checks the results.

The improver step is conditional: a draft that passes the code checks on the first review is saved without it.

## Delivery pipeline

```mermaid
flowchart LR
    push["git push to main"] --> ci

    subgraph gha["GitHub Actions"]
        direction TB
        ci["CI workflow<br/>ruff · pytest · eslint · build · Docker build"]
        cd["Deploy workflow<br/>build images · health checks"]
        ci -->|"success on main"| cd
    end

    subgraph gcp["Google Cloud"]
        direction TB
        wif["Workload Identity Federation<br/>this repo · main · production env"]
        ar[("Artifact Registry<br/>images tagged with the commit")]
        run["Cloud Run<br/>backend + frontend: new revisions"]
        job["Migration job<br/>image updated, never executed"]
    end

    cd <-->|"OIDC token ⇄ short-lived Google token<br/>(no JSON key)"| wif
    cd -->|"docker push"| ar
    cd -->|"update image"| run
    cd -.->|"update image only"| job
    gcp ~~~ tf["Terraform, run by the maintainer<br/>APIs · IAM · secrets · services · WIF · monitoring"]
    tf -.->|"provisions"| gcp
```

Terraform owns the infrastructure and its settings. The Deploy workflow owns only which image runs: Terraform ignores image changes, so a later `terraform apply` never rolls a deployment back.

## Components

| Component | Implementation |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router 7. Built into static files and served by nginx (multi-stage Docker image). |
| Backend | FastAPI, Pydantic, SQLAlchemy 2, Alembic. One process (uvicorn) per Cloud Run instance. |
| Agents | OpenAI Agents SDK, `gpt-4.1-mini`. Six agents with typed Pydantic outputs; research and contact discovery use the hosted web search tool. |
| Authentication | Supabase Auth in the browser. The backend verifies each JWT (signature via the project's public keys, expiry, audience, issuer) in one dependency, `get_current_user`. |
| Data | PostgreSQL 17 on Supabase. Every query is filtered by the user's organisation; row-level security blocks Supabase's public Data API. |
| Gmail | OAuth 2.0 with PKCE and a one-time state, `gmail.compose` scope. Refresh tokens are stored per user, encrypted with Fernet. |
| Hosting | Cloud Run services (scale 0 to 1), a Cloud Run Job for migrations, Artifact Registry, Secret Manager. |
| Delivery | GitHub Actions (CI and Deploy), Workload Identity Federation, Terraform. |
| Observability | OpenAI traces per draft (sensitive data off), token and cost per run, JSON logs in Cloud Logging, an uptime check and two email alerts in Cloud Monitoring. |

## Design decisions

- **The AI proposes, code decides.** The Reviewer's verdict is stored but not trusted: code checks that every flagged quote exists in the email, rejects placeholders and applies the score threshold. A person approves every email.
- **Bounded loops.** At most two improvements, so cost and latency are predictable.
- **Structured output everywhere.** Agents return Pydantic models, so the backend never parses free text.
- **Least privilege.** Each Cloud Run service has its own service account; the frontend's has no roles. The GitHub deployer can push images and roll out revisions, but cannot read secrets or change IAM.
- **No long-lived cloud keys.** GitHub Actions signs in through Workload Identity Federation.
- **Migrations are a deliberate step.** CD updates the migration job's image but never runs it.
- **Generation runs inside the request.** This keeps the MVP simple: a draft takes several agent calls in one request, and the backend's Cloud Run timeout is 10 minutes. A job queue is the next step for longer workloads.
