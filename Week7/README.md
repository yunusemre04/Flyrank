# AI Workflow Builder

A visual builder for AI decision workflows. Each node asks an LLM a yes/no
question; the answer picks which edge (YES or NO) the workflow follows next.
The graph is edited with **React Flow** and executed durably with **Inngest**,
using the **OpenAI SDK** for the decisions and **shadcn**-style components
for the UI.

```
"Is this a support request?"
  ├─ YES → "Is it urgent?"       → ...
  └─ NO  → "Is it a high-value lead?" → ...
```

## 1. Setup

```bash
npm install
cp .env.example .env.local
# then edit .env.local and add your OPENAI_API_KEY
```

You need **two terminals** running at the same time:

```bash
# Terminal 1 — the Next.js app
npm run dev

# Terminal 2 — the Inngest Dev Server (executes the workflow function)
npm run inngest:dev
```

Open the Inngest dev dashboard at **http://localhost:8288** to watch function
runs, and the app itself at **http://localhost:3000**.

> The Dev Server needs to reach `http://localhost:3000/api/inngest` to
> discover and invoke your function — that's what `npm run inngest:dev`
> points at by default.

## 2. Using it

- **Add a node** — click *Node* in the toolbar, then edit its title and
  prompt directly on the card.
- **Connect nodes** — drag from the green `YES` handle or red `NO` handle
  on the right of a node to the target node's input handle on the left.
  A node can have at most one YES edge and one NO edge.
- **Run** — click *Run*. The start node is auto-detected as whichever node
  has no incoming edges. Execution streams back into the canvas: the active
  node pulses blue, traversed edges animate, and each step appears in the
  **Execution Log** panel on the right with its YES/NO result.
- **Save / Load** — stores the current graph in the browser's `localStorage`.
- **Export / Import** — download the graph as `workflow.json`, or load one
  back in (handy for sharing a workflow or checking it into git).

A three-node example ("support vs. sales" triage) is loaded by default.

## 3. How it works

```
Browser (React Flow + Zustand)
   │  POST /api/run  { graph, startNodeId }
   ▼
Next.js route  ──send event "workflow/execute"──▶  Inngest
   │                                                   │
   │                                     executes `executeWorkflow`
   │                                     one step.run() per node:
   │                                       1. call OpenAI → YES/NO
   │                                       2. record the step
   │                                       3. follow the matching edge
   │                                       4. repeat until a leaf node
   ▼
Browser polls GET /api/execution/:runId every ~900ms
   for the current node, traversed edges, and step log
```

- **lib/inngest/functions.ts** — the actual workflow engine. Each node is
  wrapped in its own `step.run()`, so Inngest can retry a single failing
  step (e.g. a flaky OpenAI call) without re-running earlier, already-
  completed steps, and the whole run survives a server restart because
  Inngest persists step state.
- **lib/openai.ts** — forces the model to answer with exactly `YES` or
  `NO` (strict system prompt + `max_tokens`), and retries once with a
  stricter nudge if it doesn't comply.
- **lib/executionStore.ts** — a small in-memory store the running Inngest
  function writes to and the frontend polls. This is intentionally simple;
  see "Limitations" below for how to make it production-grade.
- **components/flow/** — the React Flow canvas, the custom decision node,
  the custom YES/NO edge, the toolbar, and the execution log panel.

## 4. Requirements checklist

**Phase 1 — Setup**
- [x] Next.js app, React Flow, Inngest, OpenAI SDK, shadcn-style components
- [x] `.env.example` for configuration
- [x] Project structure under `app/`, `components/`, `lib/`

**Phase 2 — Foundations**
- [x] React Flow canvas with draggable/zoomable viewport, minimap, controls
- [x] Add nodes, connect nodes, edit prompts inline on each node
- [x] Distinct YES (green) / NO (red) edge types with labels
- [x] Graph state lives in a Zustand store (local, in-browser)

**Phase 3 — Core execution**
- [x] Each node maps to one Inngest `step.run()`
- [x] Node prompt is sent to the LLM, which must answer only YES or NO
- [x] Execution follows the matching edge and continues until a leaf
- [x] Execution order is tracked and returned by the function

**Phase 4 — Polish** (6 of the suggested features)
- [x] Visual execution state (active node pulses, result-colored borders)
- [x] Execution logs panel (per-step prompt, result, timing)
- [x] Save / load workflows (localStorage)
- [x] JSON export / import
- [x] Animated active/traversed edges
- [x] Error handling (strict-format retry in `askYesNo`, Inngest step
      retries for transient failures, and an error banner in the UI)

## 5. Limitations & next steps

This is a learning/demo-scale scaffold, not a production deployment:

- `lib/executionStore.ts` is an **in-memory** `Map`. It works because the
  Inngest Dev Server calls back into the same `next dev` process, but it
  will **not** work across multiple server instances or serverless
  invocations, and it resets on restart. For production, replace it with
  Redis/a database, or swap polling for
  [Inngest's Realtime API](https://www.inngest.com/docs) to push updates
  instead.
- There's no cycle-prevention beyond a hard `MAX_STEPS` cap (50) — the
  editor doesn't currently stop you from wiring a loop.
- "Retry failed nodes" is handled two ways rather than a dedicated button:
  Inngest automatically retries a failing `step.run()` (transient errors),
  and `askYesNo` retries once if the model doesn't answer in the exact
  YES/NO format. A full per-node manual retry/resume UI would need the
  execution store to persist graph + partial progress, which is a natural
  next step.
