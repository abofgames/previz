# previz — CONTEXT

Session continuity doc. Read this first when resuming.
Last updated: **2026-08-20**.

---

## 1. What this is

**previz** — agentic pre-production. Paste a screenplay, get a shot-listed,
researched, drawn storyboard where every panel traces back to its shot spec and
to real cited sources.

Built for **Agentic Cinema: The Blockbuster Hackathon**, **Parallel track**.

- Repo: https://github.com/abofgames/previz (public, MIT, branch `main`)
- **Submission deadline: 2026-09-09, 2:00 PM PT**
- Judging: Technological Implementation, Design, Potential Impact, Quality of
  Idea — equally weighted.

### Three rules that drive every decision

1. **Google AI exclusively.** No OpenAI/Anthropic/self-hosted models anywhere in
   the code or dependency tree. Disqualifying.
2. **Parallel Search API must be used at runtime**, not name-dropped in a README.
3. **Originality is Stage-One pass/fail** — the project must be created during
   the contest period (opened 2026-07-27). This is why previz is a *new repo*
   and not a continuation of `../magazine_pipeline` (commits dated 2026-05-10).
   **Never merge those histories.**

Still required to submit: hosted project URL, ≤3-min public demo video
(YouTube/Vimeo, English), public repo with detectable OSS license (done),
Parallel track selected on the Devpost form.

---

## 2. Where it came from

`../magazine_pipeline` is a working AI comic pipeline whose *architecture* was
reused: filesystem-as-truth, EventBus→WebSocket, React Flow dataflow graph,
click-to-generate image cards, the multimodal consistency chain. previz is new
code in a new repo; the old project is a private reference only.

Its `CONTEXT.md` is still worth reading — several gotchas there were rediscovered
the hard way this session (see §7).

---

## 3. Architecture

```
brief ─┬─> look_dev ────────────────> lookboard (image)
       │
       └─> breakdown ──> research ─┬─> characters (group) ──> char_*   (image)
                        (Parallel) ├─> locations  (group) ──> loc_*    (image)
                                   └─> shots      (group) ──> shot_*   (image)

cross-edges into every shot_*: its loc_* plate, its char_* plates
optional, flag-gated: shot_* ──> animatic_* (Veo)
```

| Layer | Implementation |
|---|---|
| Breakdown | `gemini-3.5-flash` + `response_schema=ScriptBreakdown` |
| Scene research | ADK `LlmAgent` + `FunctionTool(parallel_search)`, 2-3 searches/scene |
| Entity research | Direct Parallel searches feeding prompts that already run |
| Plates & panels | `gemini-2.5-flash-image` conditioned on look refs + plates |
| Animatic | Veo, `ENABLE_VEO=0` by default |
| UI | React 18 + Vite + React Flow 11 + dagre, live over WebSocket |

**Key design decisions — do not re-debate:**

- **Filesystem is the state store.** Every step writes through `ProjectPaths`
  and checks existence before recomputing. Restart rehydrates from disk.
- **The graph is dataflow, not step order.** Nodes are artifacts and the agents
  that make them; cross-edges from plates into panels *are* the reference chain.
- **Agentic only where it's genuinely agentic.** Scene research is a real ADK
  agent because deciding what to look up is the work. Everything else is a known
  DAG orchestrated directly — an agent loop there buys latency, not intelligence.
- **Images are click-to-generate**, never automatic. Iterating on a breakdown
  costs zero image quota.
- **Citations come from the tool, not the model.** `_SearchToolState` records
  what Parallel actually returned and that overrides the model's claims, so a
  fabricated URL cannot survive the round trip.
- **Search generously, reason sparingly.** Parallel is $0.001/query; Gemini is
  20 requests/day/model. Three of the four Parallel passes add *zero* model calls.

---

## 4. Where Parallel is used (the partner requirement)

| Pass | Code | Extra Gemini calls |
|---|---|---|
| Scene research | `agents/research.py` (ADK agent, 5-search budget) | 1 agent run/scene |
| Character wardrobe | `steps/entity_research.py` → plate prompt | **0** |
| Location design | `steps/entity_research.py` → plate prompt | **0** |
| Look influences | `steps/look_dev.py` → look block | **0** |

Era is detected from title/logline (`runner._period`) and threaded into every
query — wrong-period wardrobe is the most visible research failure.

**Measured value.** Same script, contemporary vs. dated 1974:
- before → *"business casual, collared shirt in a muted color"*
- after → *"1970s faded pale blue short-sleeved button-up, open collar, dark necktie"*
  (sources: `roopevintage.com/vintage-1974-shirt`, `vintageclothingguides.com/decades/70s-workwear`)

**Honest assessment:** Parallel is strong on wardrobe, period and cinematography.
It is mediocre on "what does this room look like" even after filtering, because
the open web is thin on that in prose. **Demo with a period-specific script** —
that is where the research visibly changes the output.

Results are filtered before reaching a prompt (`parallel_search.is_useful`):
20 stock-image hosts blocked, plus a heuristic dropping comma-separated keyword
lists. Everything caches per query, so re-runs re-bill nothing.

---

## 5. Verified API reality (measured, not from docs)

Probed live on 2026-08-20. **Do not trust blog posts on this; they are wrong.**

| | Free tier | Notes |
|---|---|---|
| Text, per minute | **5 requests** | `GenerateRequestsPerMinutePerProjectPerModel` |
| Text, per day | **20 requests, PER MODEL** | quota is per-model, so rolling models multiplies it |
| Image, **every** model | **`limit: 0`** | never granted, not "used up" |

Image gen checked on `gemini-2.5-flash-image`, `gemini-3-pro-image`,
`gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image`, `nano-banana-pro-preview`
and two preview variants. **All zero.** Storyboard panels require billing.

Google cut free quotas the weekend of **2025-12-06/07** (2.5 Pro removed, Flash
250→20/day, image models to "not available"). The Gemini app / AI Studio web UI
kept an image allowance — that split is why it *feels* like API access exists.

Rate limits are **per Cloud project, not per API key** — extra keys buy nothing.

Text models confirmed working *and* schema-capable on the free key:
`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3-flash-preview`,
`gemini-3.1-flash-lite`, `gemma-4-31b-it`.
(`gemini-2.5-flash-lite` and `gemini-2.0-flash` return 404 on this key.)

### How the code copes

- All Gemini calls pace through a shared 5 RPM bucket (`gemini.pace()`).
- Per-**minute** 429 → retry using the server's own `retryDelay`.
- Per-**day** 429 → do NOT retry (a daily budget will not recover in 20s);
  roll forward through `TEXT_MODEL_CHAIN`. Getting this ordering wrong cost
  160s per rollover; it is now 9s.
- Scene research is serialized (`_SCENE_CONCURRENCY = 1`).
- If the research agent's closing turn is rate-limited, its already-paid-for
  citations are salvaged — but **nothing unsynthesised is written into notes
  fields**, because those get pasted into image prompts.

---

## 6. Current state

All 9 commits pushed, working tree clean, nothing running (container removed,
no uvicorn).

**Works today on the free key:** script breakdown, scene research with real
Parallel citations, look development, wardrobe/location/influence research,
🎲 Write me a scene, 🎲 Generate a look, restart rehydration, the whole graph UI.

**Blocked on billing:** drawn plates and panels (`limit: 0`), Veo animatics.

`.env` (gitignored, chmod 600, never committed) currently has:
`GEMINI_TEXT_MODEL=gemini-3.5-flash`, **`MOCK_IMAGES=1`**, plus both keys.

> **The keys were pasted in a chat transcript — rotate both after the hackathon.**

### Run it

```bash
cd /mnt/data/Documents/previz
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev          # http://localhost:5173

# or the single-URL container (UI served by FastAPI):
docker build -t previz . && docker run -d --name previz-test \
  -p 8020:8000 --env-file .env previz     # http://localhost:8020
```

Never use `uvicorn --reload` — it deadlocks on the long-running pipeline task.
Restart with `fuser -k 8000/tcp` then relaunch.

```bash
.venv/bin/python -m backend.clients.gemini --smoke
.venv/bin/python -m backend.clients.parallel_search --smoke
```

---

## 7. Gotchas discovered

- **`MOCK_IMAGES=1`** draws placeholders while everything else stays real. This
  is how to demo before billing. Setting `GEMINI_IMAGE_MODEL=""` does **not**
  force mock — the factory keys off `GEMINI_API_KEY`.
- A daily-quota 429 also carries a `retryDelay`; that delay refers only to the
  per-minute throttle. Check `PerDay` **before** the per-minute retry branch.
- ADK issues its own Gemini calls that bypass the client wrapper — the only
  place to pace them is `agents/research.py` before `runner.run_async`.
- `McpToolset` is not importable from `google.adk.tools.mcp_tool` in ADK 2.7.1.
  Irrelevant — Parallel goes through its Python SDK in a `FunctionTool`.
- React Flow: keep the **two separate effects** in `Graph.tsx` — structure
  changes recompute dagre, data changes patch in place. Merging them re-mounts
  every node and makes the graph flicker.
- `className="nodrag nowheel"` on every input, or React Flow eats the events.
- `python-multipart` is a separate install, needed for `Form`/`UploadFile`.
- Vite binds `[::1]:5173`; `curl 127.0.0.1:5173` fails but the browser works.
- Cloud Run's filesystem is ephemeral — generated artifacts vanish on recycle.
  Fine for a demo; use a GCS volume mount for persistence. Set
  `--min-instances 1` before recording the video so a cold start doesn't eat
  the first ten seconds.

---

## 8. Next session — do these in order

1. **If the $100 GCP credits have landed** (requested 2026-08-20; the request
   deadline was 2026-08-31):
   - Enable billing on the Cloud project behind `GEMINI_API_KEY`.
   - Set `MOCK_IMAGES=0`, raise `GEMINI_RPM`. **No other code change is needed** —
     the reference chain is already exercised and proven end to end.
   - Re-verify: `python -m backend.clients.gemini --smoke` should write a real PNG.
   - Draw a full storyboard and judge the actual consistency chain
     (look refs → plates → panels). This is the first time it can be assessed.
2. **Deploy to Cloud Run** for the hosted URL the submission requires.
   `gcloud` is **not installed** on this machine (`yay -S google-cloud-cli`).
   Full command is in the README.
3. **Record the 3-minute demo video.** Use a **period-specific script** — that is
   where Parallel visibly changes the output and the citations tell a story.
4. Submit on Devpost, Parallel track.

### Deferred / known-thin

- Location research quality is mediocre; wardrobe and cinematography are strong.
- `enrich`-style scene expansion, multi-project support, auth — never built,
  not needed.
- Veo animatics are wired (`panels.gen_animatic`) but untested — no free tier.
- `_salvage` currently returns citations with empty notes; a re-run synthesises
  properly. Fine, but the card should perhaps auto-retry once.
