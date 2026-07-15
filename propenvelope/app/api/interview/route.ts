/**
 * POST /api/interview  { history: ChatMessage[] }  ->  InterviewTurn.
 * Returns either the next question or the finished structured summary.
 */

import { NextResponse } from "next/server";
import { nextInterviewTurn, type ChatMessage } from "@/lib/interview";

export async function POST(req: Request) {
  let history: ChatMessage[];
  try {
    const body = await req.json();
    history = Array.isArray(body?.history) ? body.history : [];
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  try {
    const turn = await nextInterviewTurn(history);
    return NextResponse.json(turn);
  } catch (err) {
    return NextResponse.json(
      { error: `Interview failed: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
