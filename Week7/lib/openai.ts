import OpenAI from "openai";
import type { DecisionResult } from "./types";

let client: OpenAI | undefined;
const getClient = () => (client ??= new OpenAI({ apiKey: process.env.OPENAI_API_KEY }));

const SYSTEM_PROMPT =
  "You are a binary decision engine inside an automated workflow. " +
  "Read the user's question and respond with exactly one word: YES or NO. " +
  "Never add punctuation, explanation, or any other text.";

function extractDecision(raw: string | undefined | null): DecisionResult | null {
  const cleaned = (raw ?? "").trim().toUpperCase();
  if (cleaned.startsWith("YES")) return "YES";
  if (cleaned.startsWith("NO")) return "NO";
  return null;
}

/**
 * Sends a node's prompt to the model and forces a strict YES/NO answer.
 * If the model doesn't comply on the first try, we nudge it once more
 * before giving up (this is separate from Inngest's own step-level
 * retries, which handle transient network/API failures).
 */
export async function askYesNo(prompt: string): Promise<DecisionResult> {
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";

  const first = await getClient().chat.completions.create({
    model,
    temperature: 0,
    max_tokens: 5,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: prompt },
    ],
  });

  const firstRaw = first.choices[0]?.message?.content;
  const firstDecision = extractDecision(firstRaw);
  if (firstDecision) return firstDecision;

  const retry = await getClient().chat.completions.create({
    model,
    temperature: 0,
    max_tokens: 5,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: prompt },
      { role: "assistant", content: firstRaw ?? "" },
      { role: "user", content: "Reply with only the single word YES or only the single word NO." },
    ],
  });

  const retryDecision = extractDecision(retry.choices[0]?.message?.content);
  if (retryDecision) return retryDecision;

  throw new Error(
    `Model did not return a valid YES/NO answer (got: "${firstRaw ?? "empty response"}")`
  );
}
