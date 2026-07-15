/**
 * Shared Anthropic client + model config. Server-side only — never import this
 * into a client component (it reads ANTHROPIC_API_KEY).
 */

import Anthropic from "@anthropic-ai/sdk";

/**
 * The SPEC names `claude-sonnet-4-6`, which is not a current model id. We
 * default to a current Claude Sonnet and allow an env override so the id can be
 * updated without a code change. Verify against the latest model list at build.
 */
export const DEFAULT_MODEL = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-5";

let client: Anthropic | null = null;

export function getAnthropic(): Anthropic {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error(
      "ANTHROPIC_API_KEY is not set — copy .env.example to .env.local and add a key.",
    );
  }
  if (!client) {
    client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }
  return client;
}
