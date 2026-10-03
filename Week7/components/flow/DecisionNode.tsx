"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

import { useFlowStore } from "@/lib/store";
import type { DecisionNodeData } from "@/lib/types";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

function DecisionNodeComponent({ id, data, selected }: NodeProps<DecisionNodeData>) {
  const updateNodePrompt = useFlowStore((s) => s.updateNodePrompt);
  const updateNodeLabel = useFlowStore((s) => s.updateNodeLabel);
  const deleteNode = useFlowStore((s) => s.deleteNode);
  const currentNodeId = useFlowStore((s) => s.currentNodeId);
  const logs = useFlowStore((s) => s.logs);

  const isActive = currentNodeId === id;
  const lastLog = [...logs].reverse().find((l) => l.nodeId === id);
  const result = lastLog?.result;

  return (
    <div
      className={cn(
        "w-72 rounded-xl border-2 bg-card text-card-foreground shadow-md transition-all duration-300",
        isActive && "animate-pulse border-blue-500 shadow-lg shadow-blue-500/30",
        !isActive && result === "YES" && "border-emerald-500",
        !isActive && result === "NO" && "border-rose-500",
        !isActive && !result && "border-border",
        selected && "ring-2 ring-primary ring-offset-2"
      )}
    >
      <Handle type="target" position={Position.Left} className="!h-3 !w-3 !bg-slate-400" />

      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <Input
          value={data.label}
          onChange={(e) => updateNodeLabel(id, e.target.value)}
          className="nodrag h-7 border-none bg-transparent px-1 text-sm font-medium shadow-none focus-visible:ring-1"
        />
        <div className="flex shrink-0 items-center gap-1">
          {result && (
            <Badge
              className={cn(
                result === "YES"
                  ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                  : "bg-rose-100 text-rose-700 hover:bg-rose-100"
              )}
            >
              {result}
            </Badge>
          )}
          <button
            onClick={() => deleteNode(id)}
            className="nodrag px-1 text-xs text-muted-foreground hover:text-destructive"
            title="Delete node"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="px-3 py-2">
        <Textarea
          value={data.prompt}
          onChange={(e) => updateNodePrompt(id, e.target.value)}
          placeholder="Ask a yes/no question for the model..."
          className="nodrag min-h-[70px] resize-none text-xs"
        />
      </div>

      <div className="flex items-center justify-between px-3 pb-2 text-[10px] font-medium">
        <span className="text-emerald-600">YES →</span>
        <span className="text-rose-600">NO →</span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="yes"
        style={{ top: "35%" }}
        className="!h-3 !w-3 !bg-emerald-500"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="no"
        style={{ top: "65%" }}
        className="!h-3 !w-3 !bg-rose-500"
      />
    </div>
  );
}

export const DecisionNode = memo(DecisionNodeComponent);
