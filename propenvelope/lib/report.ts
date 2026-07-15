/**
 * Feasibility report composer. The LLM NARRATES deterministic inputs — it may
 * not invent zoning numbers (SPEC non-negotiable). We pass it the feasibility
 * bundle + interview JSON and constrain it hard in the system prompt.
 */

import { getAnthropic, DEFAULT_MODEL } from "@/lib/anthropic";
import type { FeasibilityInputs } from "@/lib/feasibility";
import type { IntakeSummary } from "@/lib/interview";

const DISCLAIMER =
  "This is a screening estimate, not legal or architectural advice. " +
  "Verify every figure with a NYC registered architect or expediter before filing or building.";

const SYSTEM_PROMPT = `You compose NYC property feasibility reports for PropEnvelope.

ABSOLUTE RULES:
- You may ONLY state zoning numbers that appear in the JSON provided. Never invent or estimate FAR,
  yard, coverage, height, or square-footage values. If a number is null or listed in dataGaps, say it is
  unavailable and must be confirmed — do not fill it in.
- For every zoning figure you cite, name its source field (e.g. "PLUTO.lotarea", "PLUTO.residfar",
  or "rules engine"). Provenance is required.
- Treat any district marked verified:false, and any item in dataGaps or flags, as an explicit uncertainty
  to surface — never smooth it over.
- End the report with the provided disclaimer verbatim.

Write in clear, friendly prose for a homeowner. Use these sections as markdown headings:
1. Lot Snapshot
2. Remaining Envelope
3. Your Project vs. the Envelope
4. Flags & Unknowns (include likely DOB filing type — Alt-1 vs Alt-2 — as a POSSIBILITY, not a determination)
5. Suggested Next Steps`;

export interface ReportResult {
  markdown: string;
  model: string;
}

/** Compose the report. Returns markdown ending in the standard disclaimer. */
export async function composeReport(
  feasibility: FeasibilityInputs,
  intake: IntakeSummary,
): Promise<ReportResult> {
  const anthropic = getAnthropic();

  const userContent = [
    "Compose the feasibility report from these deterministic inputs.",
    "",
    "## FEASIBILITY_JSON (the only source of zoning numbers you may cite)",
    "```json",
    JSON.stringify(feasibility, null, 2),
    "```",
    "",
    "## INTERVIEW_JSON (the homeowner's project intent)",
    "```json",
    JSON.stringify(intake, null, 2),
    "```",
    "",
    `End with this disclaimer verbatim: "${DISCLAIMER}"`,
  ].join("\n");

  const resp = await anthropic.messages.create({
    model: DEFAULT_MODEL,
    max_tokens: 2048,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userContent }],
  });

  let markdown = resp.content
    .filter((b) => b.type === "text")
    .map((b) => (b.type === "text" ? b.text : ""))
    .join("\n")
    .trim();

  // Belt-and-suspenders: guarantee the disclaimer is present.
  if (!markdown.includes("not legal or architectural advice")) {
    markdown += `\n\n---\n\n_${DISCLAIMER}_`;
  }

  return { markdown, model: DEFAULT_MODEL };
}
