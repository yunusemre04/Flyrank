import { NextRequest, NextResponse } from "next/server";

import { getRun } from "@/lib/executionStore";

export async function GET(_req: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const state = getRun(runId);

  if (!state) {
    return NextResponse.json({ error: "run not found" }, { status: 404 });
  }

  return NextResponse.json(state);
}
