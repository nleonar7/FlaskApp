/**
 * AI interview orchestration. A short (5–8 turn) conversational intake that
 * ends in a structured JSON summary. The interview gathers *design intent* — it
 * has nothing to do with zoning math (that stays deterministic in lib/zoning).
 */

import { getAnthropic, DEFAULT_MODEL } from "@/lib/anthropic";
import { z } from "zod";

export const PROJECT_TYPES = [
  "addition",
  "adu",
  "garage-conversion",
  "deck",
  "interior-reconfig",
  "other",
] as const;

export const IntakeSummarySchema = z.object({
  projectType: z.enum(PROJECT_TYPES),
  desiredSizeSqft: z.number().nullable(),
  budgetBand: z
    .enum(["under-50k", "50k-150k", "150k-400k", "over-400k", "unsure"])
    .nullable(),
  usage: z.array(z.string()).describe("How they use the home: hosting, WFH, hobbies…"),
  stylePreferences: z.array(z.string()),
  notes: z.string(),
});

export type IntakeSummary = z.infer<typeof IntakeSummarySchema>;

export type ChatMessage = { role: "user" | "assistant"; content: string };

const SYSTEM_PROMPT = `You are the intake interviewer for PropEnvelope, a NYC property feasibility tool.
Run a warm, efficient 5–8 question interview to understand what the homeowner wants to BUILD or CHANGE.
Cover, in a natural order: project type (addition / ADU / garage conversion / deck / interior reconfiguration),
rough desired size, budget band, how they use the home (hosting, hobbies, work-from-home), and style preferences.
Ask ONE question at a time. Keep questions short and friendly. Do not discuss zoning, FAR, setbacks, or feasibility —
that is computed separately from official data. When you have enough to summarize (usually after 5–8 answers),
call the \`submit_intake\` tool with the structured summary instead of asking another question.`;

const INTAKE_TOOL = {
  name: "submit_intake",
  description:
    "Record the finished intake summary. Call this only when the interview has gathered enough to summarize.",
  input_schema: {
    type: "object" as const,
    properties: {
      projectType: { type: "string", enum: [...PROJECT_TYPES] },
      desiredSizeSqft: { type: ["number", "null"] },
      budgetBand: {
        type: ["string", "null"],
        enum: ["under-50k", "50k-150k", "150k-400k", "over-400k", "unsure", null],
      },
      usage: { type: "array", items: { type: "string" } },
      stylePreferences: { type: "array", items: { type: "string" } },
      notes: { type: "string" },
    },
    required: ["projectType", "usage", "stylePreferences", "notes"],
  },
};

export type InterviewTurn =
  | { done: false; question: string }
  | { done: true; summary: IntakeSummary };

/**
 * Advance the interview by one turn. Pass the full prior transcript; returns
 * either the next question or (when the model calls submit_intake) the summary.
 */
export async function nextInterviewTurn(
  history: ChatMessage[],
): Promise<InterviewTurn> {
  const anthropic = getAnthropic();

  // Seed the very first turn so the model opens the conversation.
  const messages =
    history.length === 0
      ? [{ role: "user" as const, content: "Start the interview." }]
      : history;

  const resp = await anthropic.messages.create({
    model: DEFAULT_MODEL,
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    tools: [INTAKE_TOOL],
    messages,
  });

  const toolUse = resp.content.find((b) => b.type === "tool_use");
  if (toolUse && toolUse.type === "tool_use") {
    const parsed = IntakeSummarySchema.safeParse(toolUse.input);
    if (parsed.success) {
      return { done: true, summary: parsed.data };
    }
    // Malformed tool call — fall through to ask the user to clarify.
  }

  const text = resp.content
    .filter((b) => b.type === "text")
    .map((b) => (b.type === "text" ? b.text : ""))
    .join("\n")
    .trim();

  return { done: false, question: text || "Could you tell me a bit more?" };
}
