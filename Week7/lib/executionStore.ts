import type { ExecutionState, ExecutionStep } from "./types";

/**
 * Simple in-memory store for run state.
 *
 * This is intentionally minimal: it works because, in local development,
 * the Inngest Dev Server invokes your Next.js function via HTTP calls back
 * into the SAME running Next.js process (the one started by `next dev`).
 * We stash the Map on `globalThis` so it survives Next.js's hot-module
 * reloads in dev.
 *
 * For a production deployment you'd swap this for Redis, a database, or
 * Inngest's Realtime API so state survives across serverless invocations
 * and multiple instances.
 */

const globalForStore = globalThis as unknown as {
  __executionStore?: Map<string, ExecutionState>;
};

const store = globalForStore.__executionStore ?? new Map<string, ExecutionState>();
globalForStore.__executionStore = store;

export function createRun(runId: string): ExecutionState {
  const state: ExecutionState = {
    runId,
    status: "running",
    steps: [],
    visitedEdgeIds: [],
    startedAt: Date.now(),
  };
  store.set(runId, state);
  return state;
}

export function getRun(runId: string): ExecutionState | undefined {
  return store.get(runId);
}

export function updateRun(runId: string, patch: Partial<ExecutionState>) {
  const current = store.get(runId);
  if (!current) return;
  store.set(runId, { ...current, ...patch });
}

export function addStep(runId: string, step: ExecutionStep) {
  const current = store.get(runId);
  if (!current) return;
  store.set(runId, { ...current, steps: [...current.steps, step] });
}

export function markEdgeVisited(runId: string, edgeId: string) {
  const current = store.get(runId);
  if (!current) return;
  store.set(runId, {
    ...current,
    visitedEdgeIds: [...current.visitedEdgeIds, edgeId],
  });
}
