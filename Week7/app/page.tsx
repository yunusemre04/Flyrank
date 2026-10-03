import { FlowCanvas } from "@/components/flow/FlowCanvas";
import { Toolbar } from "@/components/flow/Toolbar";
import { LogsPanel } from "@/components/flow/LogsPanel";

export default function Home() {
  return (
    <main className="flex h-screen w-screen flex-col overflow-hidden">
      <Toolbar />
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1">
          <FlowCanvas />
        </div>
        <LogsPanel />
      </div>
    </main>
  );
}
