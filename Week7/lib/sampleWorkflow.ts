import type { WorkflowGraph } from "./types";

export const sampleWorkflow: WorkflowGraph = {
  nodes: [
    {
      id: "start",
      type: "decisionNode",
      position: { x: 40, y: 160 },
      data: {
        label: "Is this a support request?",
        prompt:
          "Customer message: \"My order hasn't arrived and I was charged twice.\" " +
          "Is this a customer support request?",
      },
    },
    {
      id: "support",
      type: "decisionNode",
      position: { x: 440, y: 30 },
      data: {
        label: "Is it urgent?",
        prompt:
          "Customer message: \"My order hasn't arrived and I was charged twice.\" " +
          "Does this need to be escalated to a human agent within the hour?",
      },
    },
    {
      id: "sales",
      type: "decisionNode",
      position: { x: 440, y: 300 },
      data: {
        label: "Is it a high-value lead?",
        prompt:
          "Customer message: \"My order hasn't arrived and I was charged twice.\" " +
          "Does this look like a high-value sales lead worth a personal follow-up?",
      },
    },
  ],
  edges: [
    {
      id: "e-start-support-yes",
      source: "start",
      target: "support",
      sourceHandle: "yes",
      type: "decisionEdge",
      data: { type: "yes" },
    },
    {
      id: "e-start-sales-no",
      source: "start",
      target: "sales",
      sourceHandle: "no",
      type: "decisionEdge",
      data: { type: "no" },
    },
  ],
};
