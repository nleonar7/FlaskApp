/**
 * POST /api/report  { feasibility, intake }  ->  { markdown, model }.
 * The LLM narrates the deterministic feasibility bundle only.
 */

import { NextResponse } from "next/server";
import { composeReport } from "@/lib/report";
import { IntakeSummarySchema } from "@/lib/interview";

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (!body?.feasibility) {
    return NextResponse.json({ error: "Missing `feasibility`." }, { status: 400 });
  }
  const intake = IntakeSummarySchema.safeParse(body?.intake);
  if (!intake.success) {
    return NextResponse.json(
      { error: "Invalid `intake` summary.", issues: intake.error.issues },
      { status: 400 },
    );
  }

  try {
    const result = await composeReport(body.feasibility, intake.data);
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: `Report generation failed: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
