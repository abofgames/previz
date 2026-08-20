# previz

**Agentic pre-production.** Paste a screenplay; get a shot-listed, researched,
drawn storyboard — with every panel traceable back to the shot spec and the
real, cited sources that informed it.

Built for **Agentic Cinema: The Blockbuster Hackathon** · **Parallel track**.

---

## What it does

An art department spends weeks on this. previz runs it as an agent graph you
watch execute:

1. **Script breakdown** — Gemini reads the screenplay and extracts characters,
   locations, scenes, and a real shot list: size, lens, angle, movement, one
   row per frame of coverage.
2. **Visual research** — an ADK agent decides what it needs to know, searches
   the live web through the **Parallel Search API**, and writes a dossier per
   scene: period accuracy, wardrobe, architecture, how a named director
   actually shoots this kind of scene. Every claim carries a source URL.
3. **Look development** — the director's reference frames and look note become
   a palette, a lighting approach, a lens character.
4. **Reference plates** — one clean plate per character and per location,
   grounded in the research and rendered in the film's look.
5. **Storyboard panels** — each panel is generated with the look, the location
   plate, and every character plate attached. That reference chain is what
   keeps the same character recognisable from shot 3 to shot 12.

Plates and panels are **click-to-generate**, so iterating on the breakdown
costs no image quota.

## Why the research layer matters

Any tool can turn a prompt into a picture. The hard part of pre-production is
being *right*: the coat is wrong for the decade, the building didn't look like
that, the director never shoots a scene like that. previz searches for the
answer before it draws, and shows you what it read.

---

## Where Google Cloud and Parallel are used at runtime

| Service | Where | What it does |
|---|---|---|
| **Gemini 2.5 Flash** | `backend/clients/gemini.py` → `GeminiText` | Script breakdown and look block via `response_schema`; writes every plate and panel prompt |
| **Gemini 2.5 Flash Image** | `backend/clients/gemini.py` → `GeminiImage` | Generates plates and panels, conditioned on inline reference images |
| **Google ADK** | `backend/agents/research.py` | The research agent — `LlmAgent` on Gemini, driven by `Runner`, with the Parallel search tool |
| **Veo** (optional) | `backend/clients/gemini.py` → `GeminiImage.animate` | Turns a panel into an animatic clip. Off by default — Veo has no free tier |
| **Parallel Search API** | `backend/clients/parallel_search.py` | Live web search, called by the agent as a `FunctionTool`; results are normalized to citations, cached per query, and surfaced in the UI |

No other AI provider is used anywhere in this codebase or its dependency tree.

---

## Run it

```bash
git clone https://github.com/abofgames/previz.git && cd previz
cp .env.example .env          # add your keys — see below
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Paste a screenplay into the **Script Breakdown** card, optionally drop
reference frames and a look note into **Look Development**, and hit
**Break down script**. When the graph fans out, click **Draw** on any plate or
panel.

### Keys

| Variable | Where to get it | Needed for |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — free tier works | All reasoning and image generation |
| `PARALLEL_API_KEY` | [platform.parallel.ai](https://platform.parallel.ai) | Live visual research |

**Both are optional.** With placeholder keys the app runs end to end on mock
clients — canned breakdown, Pillow placeholder images, mock citations — so you
can see the whole flow before spending a single token.

`gemini-2.5-flash-image` is the image model because it has a real free daily
quota; `gemini-3-pro-image` is 0 RPD on the free tier. Check your own limits at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit).

### Smoke tests

```bash
.venv/bin/python -m backend.clients.gemini --smoke           # text + one image round-trip
.venv/bin/python -m backend.clients.parallel_search --smoke  # prints live titles + URLs
```

---

## Host it

The container builds the UI and serves it from the Python app, so the whole
thing is **one service on one URL** — no CORS, no separate frontend host, and
the WebSocket rides the same origin.

```bash
docker build -t previz .
docker run -p 8000:8000 --env-file .env previz     # http://localhost:8000
```

### Cloud Run (recommended — this is the hosted URL for the submission)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

gcloud run deploy previz \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=...,PARALLEL_API_KEY=..." \
  --memory 1Gi --timeout 900
```

`gcloud run deploy --source .` builds the Dockerfile with Cloud Build and
returns a public `https://previz-....run.app` URL. Cloud Run supports
WebSockets natively, so the live graph works as-is.

Two things to know about Cloud Run and this app:

- **Its filesystem is ephemeral.** previz uses the filesystem as its state
  store, so generated artifacts vanish when an instance recycles. Fine for a
  demo; for anything persistent, back `PROJECTS_ROOT` with a GCS bucket
  mount (`--add-volume` / `--add-volume-mount`).
- **Set `--min-instances 1`** before recording the demo video, so a cold start
  doesn't eat the first ten seconds.

Prefer secrets over `--set-env-vars` for a real deployment:

```bash
echo -n "YOUR_KEY" | gcloud secrets create gemini-api-key --data-file=-
gcloud run deploy previz --source . --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"
```

### Anywhere else

Any host that runs a container and passes WebSockets works — Fly.io
(`fly launch`), Render, Railway. Cloud Run is the recommendation here because
the hackathon judges runtime use of Google Cloud.

---

## How it's built

**The filesystem is the state store.** Every step writes its artifact to a path
owned by `ProjectPaths` and checks for it before recomputing. A backend restart
rehydrates the whole graph from disk instead of dropping you back to an empty
canvas, and nothing regenerates an image you already paid for.

**The graph is dataflow, not step order.** Nodes are artifacts and the agents
that produce them; edges are real dependencies. Cross-edges from each plate
into the panels that use it are the reference chain, drawn.

**Agentic where it's genuinely agentic.** Research is a real ADK agent with a
tool and a search budget, because deciding what to look up is the actual work.
The rest of the pipeline is a known DAG, orchestrated directly — wrapping a
fixed sequence in an agent loop buys latency, not intelligence.

**The citations come from the tool, not the model.** The search wrapper records
what it actually returned, and that record overrides whatever the model claims
it read. A fabricated URL cannot survive the round trip.

```
backend/
  models.py       Pydantic domain + graph models
  project.py      ProjectPaths — the on-disk contract
  runner.py       graph construction, fan-out, per-card generation, rehydration
  agents/         the ADK research agent
  clients/        Gemini, Parallel, and the mock fallbacks
  steps/          one module per artifact kind
frontend/src/graph/   React Flow canvas, live over WebSocket
```

## License

MIT — see [LICENSE](LICENSE).
