export type DecisionResult = "YES" | "NO";

export interface DecisionNodeData {
  label: string;
  prompt: string;
  status?: "idle" | "active" | "success" | "error";
}

export interface ExecutionStep {
  nodeId: string;
  label: string;
  prompt: string;
  result?: DecisionResult;
  startedAt: number;
  finishedAt?: number;
}

export interface ExecutionState {
  runId: string;
  status: "running" | "completed" | "failed";
  currentNodeId?: string;
  steps: ExecutionStep[];
  visitedEdgeIds: string[];
  error?: string;
  startedAt: number;
  finishedAt?: number;
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: DecisionNodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  type?: string;
  data?: { type: "yes" | "no" };
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}
