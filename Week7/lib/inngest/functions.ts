import { inngest } from "./client";
import { askYesNo } from "@/lib/openai";
import { createRun, updateRun, addStep, markEdgeVisited } from "@/lib/executionStore";
import type { WorkflowGraph } from "@/lib/types";

// Guards against accidental cycles in a hand-built graph.
const MAX_STEPS = 50;

export const executeWorkflow = inngest.createFunction(
  { id: "execute-workflow", retries: 1, triggers: [{ event: "workflow/execute" }] },
  async ({ event, step }) => {
    const { graph, runId, startNodeId } = event.data as {
      graph: WorkflowGraph;
      runId: string;
      startNodeId: string;
    };

    // Wrapped in step.run so this only actually executes once, even if
    // Inngest replays the function body after a later step completes.
    await step.run("init-run", async () => {
      createRun(runId);
    });

    let currentNodeId: string | undefined = startNodeId;
    let iterations = 0;
    const trace: Array<{ nodeId: string; result: string }> = [];

    try {
      while (currentNodeId && iterations < MAX_STEPS) {
        iterations += 1;
        const node = graph.nodes.find((n) => n.id === currentNodeId);
        if (!node) break;

        // Each node maps to one durable Inngest step. The callback below
        // is memoized by Inngest after its first successful run, and
        // Inngest will automatically retry it on transient failures
        // (per the function's `retries` setting) before giving up.
        const result: "YES" | "NO" = await step.run(`node-${node.id}`, async () => {
          updateRun(runId, { currentNodeId: node.id });
          const startedAt = Date.now();
          const decision = await askYesNo(node.data.prompt);
          addStep(runId, {
            nodeId: node.id,
            label: node.data.label,
            prompt: node.data.prompt,
            result: decision,
            startedAt,
            finishedAt: Date.now(),
          });
          return decision;
        });

        trace.push({ nodeId: node.id, result });

        const handle = result === "YES" ? "yes" : "no";
        const edge = graph.edges.find(
          (e) => e.source === node.id && (e.sourceHandle ?? e.data?.type) === handle
        );

        if (!edge) {
          currentNodeId = undefined;
          break;
        }

        await step.run(`edge-${edge.id}`, async () => {
          markEdgeVisited(runId, edge.id);
        });

        currentNodeId = edge.target;
      }

      await step.run("finalize", async () => {
        updateRun(runId, {
          status: "completed",
          currentNodeId: undefined,
          finishedAt: Date.now(),
        });
      });

      return { runId, trace };
    } catch (err: any) {
      updateRun(runId, {
        status: "failed",
        error: err?.message ?? "Unknown error",
        finishedAt: Date.now(),
      });
      throw err;
    }
  }
);
