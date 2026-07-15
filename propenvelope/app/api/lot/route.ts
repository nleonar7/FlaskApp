/**
 * POST /api/lot  { address }  ->  FeasibilityInputs (deterministic, no LLM).
 * Fails loud with a 4xx and a machine code when data is missing (SPEC).
 */

import { NextResponse } from "next/server";
import { computeFeasibility } from "@/lib/feasibility";
import { PlutoDataError } from "@/lib/pluto";

export async function POST(req: Request) {
  let address: unknown;
  try {
    ({ address } = await req.json());
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (typeof address !== "string" || !address.trim()) {
    return NextResponse.json(
      { error: "Provide a non-empty `address`." },
      { status: 400 },
    );
  }

  try {
    const feasibility = await computeFeasibility(address);
    return NextResponse.json(feasibility);
  } catch (err) {
    if (err instanceof PlutoDataError) {
      // 404 for "not found" style, 502 for upstream unreachable.
      const status =
        err.code === "pluto_unreachable" || err.code === "geosearch_unreachable"
          ? 502
          : 404;
      return NextResponse.json({ error: err.message, code: err.code }, { status });
    }
    return NextResponse.json(
      { error: `Unexpected error: ${(err as Error).message}` },
      { status: 500 },
    );
  }
}
