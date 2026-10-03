"use client";

import { useFlowStore } from "@/lib/store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function LogsPanel() {
  const logs = useFlowStore((s) => s.logs);
  const runStatus = useFlowStore((s) => s.runStatus);
  const errorMessage = useFlowStore((s) => s.errorMessage);

  return (
    <div className="flex h-full w-80 flex-col border-l bg-background">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-semibold">Execution Log</span>
        <Badge
          variant={
            runStatus === "completed"
              ? "default"
              : runStatus === "failed"
              ? "destructive"
              : runStatus === "running"
              ? "secondary"
              : "outline"
          }
        >
          {runStatus}
        </Badge>
      </div>

      {errorMessage && (
        <div className="border-b bg-rose-50 px-3 py-2 text-xs text-rose-700">{errorMessage}</div>
      )}

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-2 p-3">
          {logs.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Run the workflow to see each decision step appear here in order.
            </p>
          )}
          {logs.map((log, idx) => (
            <div key={`${log.nodeId}-${idx}`} className="rounded-lg border p-2 text-xs">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-medium">
                  {idx + 1}. {log.label}
                </span>
                {log.result && (
                  <Badge
                    className={cn(
                      "shrink-0",
                      log.result === "YES"
                        ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                        : "bg-rose-100 text-rose-700 hover:bg-rose-100"
                    )}
                  >
                    {log.result}
                  </Badge>
                )}
              </div>
              <p className="line-clamp-3 text-muted-foreground">{log.prompt}</p>
              {log.finishedAt && log.startedAt && (
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {log.finishedAt - log.startedAt}ms
                </p>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
