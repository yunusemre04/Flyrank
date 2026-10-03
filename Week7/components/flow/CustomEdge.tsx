"use client";

import { EdgeLabelRenderer, getBezierPath, type EdgeProps } from "reactflow";

import { useFlowStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function DecisionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps<{ type: "yes" | "no" }>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const visitedEdgeIds = useFlowStore((s) => s.visitedEdgeIds);
  const isVisited = visitedEdgeIds.includes(id);
  const isYes = data?.type === "yes";

  return (
    <>
      <path
        id={id}
        d={edgePath}
        markerEnd={markerEnd}
        fill="none"
        style={{
          stroke: isYes ? "#10b981" : "#f43f5e",
          strokeWidth: isVisited ? 3 : 1.5,
        }}
        className={cn("react-flow__edge-path", isVisited && "edge-animated")}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
          className={cn(
            "nodrag nopan rounded-full border px-1.5 py-0.5 text-[9px] font-semibold",
            isYes
              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
              : "border-rose-300 bg-rose-50 text-rose-700",
            isVisited && (isYes ? "ring-2 ring-emerald-400" : "ring-2 ring-rose-400")
          )}
        >
          {isYes ? "YES" : "NO"}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
