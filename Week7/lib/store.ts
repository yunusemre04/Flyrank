"use client";

import { create } from "zustand";
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from "reactflow";
import type { DecisionNodeData, ExecutionStep } from "./types";
import { sampleWorkflow } from "./sampleWorkflow";

type RunStatus = "idle" | "running" | "completed" | "failed";

interface FlowState {
  nodes: Node<DecisionNodeData>[];
  edges: Edge[];

  runId: string | null;
  runStatus: RunStatus;
  currentNodeId: string | null;
  visitedEdgeIds: string[];
  logs: ExecutionStep[];
  errorMessage: string | null;

  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: () => void;
  updateNodePrompt: (id: string, prompt: string) => void;
  updateNodeLabel: (id: string, label: string) => void;
  deleteNode: (id: string) => void;
  setGraph: (nodes: Node<DecisionNodeData>[], edges: Edge[]) => void;

  resetExecutionVisuals: () => void;
  startRun: (runId: string) => void;
  applyExecutionState: (state: {
    status: RunStatus;
    currentNodeId?: string;
    visitedEdgeIds?: string[];
    steps?: ExecutionStep[];
    error?: string;
  }) => void;
  stopRun: (status: "completed" | "failed", errorMessage?: string) => void;
}

let nodeCounter = 0;

export const useFlowStore = create<FlowState>((set, get) => ({
  nodes: sampleWorkflow.nodes as Node<DecisionNodeData>[],
  edges: sampleWorkflow.edges as Edge[],

  runId: null,
  runStatus: "idle",
  currentNodeId: null,
  visitedEdgeIds: [],
  logs: [],
  errorMessage: null,

  onNodesChange: (changes) => set({ nodes: applyNodeChanges(changes, get().nodes) }),

  onEdgesChange: (changes) => set({ edges: applyEdgeChanges(changes, get().edges) }),

  onConnect: (connection) => {
    const type = connection.sourceHandle === "no" ? "no" : "yes";
    set({
      edges: addEdge(
        {
          ...connection,
          id: `e-${connection.source}-${connection.target}-${type}-${Date.now()}`,
          type: "decisionEdge",
          data: { type },
        },
        get().edges
      ),
    });
  },

  addNode: () => {
    nodeCounter += 1;
    const id = `node-${Date.now()}-${nodeCounter}`;
    const newNode: Node<DecisionNodeData> = {
      id,
      type: "decisionNode",
      position: { x: 160 + Math.random() * 200, y: 120 + Math.random() * 320 },
      data: {
        label: `Decision ${nodeCounter}`,
        prompt: "Is this...?",
      },
    };
    set({ nodes: [...get().nodes, newNode] });
  },

  updateNodePrompt: (id, prompt) =>
    set({
      nodes: get().nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, prompt } } : n)),
    }),

  updateNodeLabel: (id, label) =>
    set({
      nodes: get().nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label } } : n)),
    }),

  deleteNode: (id) =>
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
    }),

  setGraph: (nodes, edges) => set({ nodes, edges }),

  resetExecutionVisuals: () =>
    set({
      runId: null,
      runStatus: "idle",
      currentNodeId: null,
      visitedEdgeIds: [],
      logs: [],
      errorMessage: null,
    }),

  startRun: (runId) =>
    set({
      runId,
      runStatus: "running",
      currentNodeId: null,
      visitedEdgeIds: [],
      logs: [],
      errorMessage: null,
    }),

  applyExecutionState: (state) =>
    set({
      runStatus: state.status,
      currentNodeId: state.currentNodeId ?? null,
      visitedEdgeIds: state.visitedEdgeIds ?? [],
      logs: state.steps ?? [],
      errorMessage: state.error ?? null,
    }),

  stopRun: (status, errorMessage) =>
    set({ runStatus: status, currentNodeId: null, errorMessage: errorMessage ?? null }),
}));
