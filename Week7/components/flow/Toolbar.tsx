"use client";

import { useCallback, useRef, useState, type ChangeEvent } from "react";
import { Download, FolderOpen, Loader2, Play, Plus, RotateCcw, Save, Upload } from "lucide-react";

import { useFlowStore } from "@/lib/store";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "ai-workflow-builder:saved-workflow";
const POLL_INTERVAL_MS = 900;
const MAX_404_RETRIES = 20;

function findStartNodeId(nodes: { id: string }[], edges: { target: string }[]) {
  const targets = new Set(edges.map((e) => e.target));
  const candidate = nodes.find((n) => !targets.has(n.id));
  return candidate?.id ?? nodes[0]?.id;
}

export function Toolbar() {
  const nodes = useFlowStore((s) => s.nodes);
  const edges = useFlowStore((s) => s.edges);
  const addNode = useFlowStore((s) => s.addNode);
  const setGraph = useFlowStore((s) => s.setGraph);
  const startRun = useFlowStore((s) => s.startRun);
  const applyExecutionState = useFlowStore((s) => s.applyExecutionState);
  const stopRun = useFlowStore((s) => s.stopRun);
  const resetExecutionVisuals = useFlowStore((s) => s.resetExecutionVisuals);
  const runStatus = useFlowStore((s) => s.runStatus);

  const [isStarting, setIsStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleRun = useCallback(async () => {
    if (nodes.length === 0) return;
    const startNodeId = findStartNodeId(nodes, edges);
    if (!startNodeId) return;

    setIsStarting(true);
    resetExecutionVisuals();

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph: { nodes, edges }, startNodeId }),
      });
      if (!res.ok) throw new Error("Failed to start the run");
      const { runId } = await res.json();
      startRun(runId);

      let missCount = 0;
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`/api/execution/${runId}`);
          if (r.status === 404) {
            missCount += 1;
            // The Inngest dev server may take a beat to pick up the event.
            if (missCount > MAX_404_RETRIES) {
              stopPolling();
              stopRun(
                "failed",
                "The run never started. Is the Inngest dev server running? (npm run inngest:dev)"
              );
            }
            return;
          }
          const state = await r.json();
          applyExecutionState(state);
          if (state.status === "completed" || state.status === "failed") {
            stopPolling();
          }
        } catch {
          // transient network hiccup while polling — keep trying
        }
      }, POLL_INTERVAL_MS);
    } catch (err: any) {
      stopRun("failed", err?.message ?? "Failed to start the run");
    } finally {
      setIsStarting(false);
    }
  }, [nodes, edges, resetExecutionVisuals, startRun, applyExecutionState, stopRun]);

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ nodes, edges }));
  };

  const handleLoad = () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    setGraph(parsed.nodes, parsed.edges);
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify({ nodes, edges }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportClick = () => fileInputRef.current?.click();

  const handleImportFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const parsed = JSON.parse(text);
    setGraph(parsed.nodes, parsed.edges);
    e.target.value = "";
  };

  const isRunning = runStatus === "running" || isStarting;

  return (
    <div className="flex flex-wrap items-center gap-2 border-b bg-background/95 px-4 py-2 backdrop-blur">
      <span className="mr-2 text-sm font-semibold">AI Workflow Builder</span>
      <div className="mx-1 h-5 w-px bg-border" />

      <Button size="sm" variant="secondary" onClick={addNode}>
        <Plus className="mr-1 h-4 w-4" /> Node
      </Button>
      <Button size="sm" onClick={handleRun} disabled={isRunning}>
        {isRunning ? (
          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
        ) : (
          <Play className="mr-1 h-4 w-4" />
        )}
        Run
      </Button>
      <Button size="sm" variant="outline" onClick={resetExecutionVisuals}>
        <RotateCcw className="mr-1 h-4 w-4" /> Reset
      </Button>

      <div className="mx-1 h-5 w-px bg-border" />

      <Button size="sm" variant="outline" onClick={handleSave}>
        <Save className="mr-1 h-4 w-4" /> Save
      </Button>
      <Button size="sm" variant="outline" onClick={handleLoad}>
        <FolderOpen className="mr-1 h-4 w-4" /> Load
      </Button>
      <Button size="sm" variant="outline" onClick={handleExport}>
        <Download className="mr-1 h-4 w-4" /> Export
      </Button>
      <Button size="sm" variant="outline" onClick={handleImportClick}>
        <Upload className="mr-1 h-4 w-4" /> Import
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        className="hidden"
        onChange={handleImportFile}
      />
    </div>
  );
}
