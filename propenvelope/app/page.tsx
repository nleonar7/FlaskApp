"use client";

import { useState } from "react";
import type { FeasibilityInputs } from "@/lib/feasibility";
import type { ChatMessage, IntakeSummary, InterviewTurn } from "@/lib/interview";
import { LotCard } from "./components/LotCard";
import { Interview } from "./components/Interview";
import { Report } from "./components/Report";

type Stage = "address" | "lot" | "interview" | "report";

export default function Home() {
  const [stage, setStage] = useState<Stage>("address");
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feasibility, setFeasibility] = useState<FeasibilityInputs | null>(null);
  const [intake, setIntake] = useState<IntakeSummary | null>(null);

  async function lookupAddress(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/lot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error ?? "Lookup failed.");
      setFeasibility(data as FeasibilityInputs);
      setStage("lot");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function onInterviewDone(summary: IntakeSummary) {
    setIntake(summary);
    setStage("report");
  }

  return (
    <main>
      <header className="mb-8 no-print">
        <h1 className="text-2xl font-bold tracking-tight">PropEnvelope</h1>
        <p className="mt-1 text-sm text-slate-600">
          NYC property feasibility, grounded in official open data. Screening
          estimate — not legal or architectural advice.
        </p>
      </header>

      {stage === "address" && (
        <form onSubmit={lookupAddress} className="space-y-3">
          <label htmlFor="address" className="block text-sm font-medium">
            NYC property address
          </label>
          <input
            id="address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="e.g. 60 Conyingham Ave, Staten Island, NY"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !address.trim()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? "Looking up…" : "Look up lot"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
      )}

      {stage === "lot" && feasibility && (
        <div className="space-y-6">
          <LotCard feasibility={feasibility} />
          <div className="flex gap-3 no-print">
            <button
              onClick={() => setStage("interview")}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            >
              This is my property — continue
            </button>
            <button
              onClick={() => {
                setStage("address");
                setFeasibility(null);
              }}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium"
            >
              Try another address
            </button>
          </div>
        </div>
      )}

      {stage === "interview" && (
        <Interview onDone={onInterviewDone} />
      )}

      {stage === "report" && feasibility && intake && (
        <Report feasibility={feasibility} intake={intake} />
      )}
    </main>
  );
}
