import { NextRequest, NextResponse } from "next/server";

import { inngest } from "@/lib/inngest/client";
import type { WorkflowGraph } from "@/lib/types";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { graph, startNodeId } = body as { graph: WorkflowGraph; startNodeId: string };

  if (!graph || !graph.nodes?.length || !startNodeId) {
    return NextResponse.json(
      { error: "graph (with at least one node) and startNodeId are required" },
      { status: 400 }
    );
  }

  const runId = crypto.randomUUID();

  await inngest.send({
    name: "workflow/execute",
    data: { graph, runId, startNodeId },
  });

  return NextResponse.json({ runId });
}
