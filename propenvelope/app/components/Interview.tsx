"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage, IntakeSummary, InterviewTurn } from "@/lib/interview";

export function Interview({
  onDone,
}: {
  onDone: (summary: IntakeSummary) => void;
}) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  async function advance(next: ChatMessage[]) {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/interview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history: next }),
      });
      const turn: InterviewTurn & { error?: string } = await resp.json();
      if (!resp.ok) throw new Error(turn.error ?? "Interview failed.");
      if (turn.done) {
        onDone(turn.summary);
        return;
      }
      setHistory([...next, { role: "assistant", content: turn.question }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // Kick off the first question once.
  useEffect(() => {
    if (!started.current) {
      started.current = true;
      void advance([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const next: ChatMessage[] = [...history, { role: "user", content: input.trim() }];
    setHistory(next);
    setInput("");
    void advance(next);
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Tell us about your project</h2>
      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        {history.map((m, i) => (
          <div
            key={i}
            className={m.role === "assistant" ? "text-slate-800" : "text-slate-500"}
          >
            <span className="mr-2 text-xs uppercase tracking-wide text-slate-400">
              {m.role === "assistant" ? "PropEnvelope" : "You"}
            </span>
            {m.content}
          </div>
        ))}
        {loading && <div className="text-sm text-slate-400">…thinking</div>}
      </div>

      <form onSubmit={send} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          placeholder="Type your answer…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Send
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
