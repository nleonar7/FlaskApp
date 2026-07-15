/**
 * CLI smoke test for the PLUTO data layer (SPEC build step 2):
 *
 *   npm run pluto -- "60 Conyingham Ave, Staten Island, NY"
 *
 * Hits the live NYC GeoSearch + PLUTO APIs and prints the full deterministic
 * feasibility bundle. No API key required. Use this to verify field mappings
 * and grab real fixture values for tests.
 */

import { computeFeasibility } from "@/lib/feasibility";
import { PlutoDataError } from "@/lib/pluto";

async function main() {
  const address = process.argv.slice(2).join(" ").trim();
  if (!address) {
    console.error('Usage: npm run pluto -- "<NYC address>"');
    process.exit(1);
  }

  try {
    const feasibility = await computeFeasibility(address);
    console.log(JSON.stringify(feasibility, null, 2));
  } catch (err) {
    if (err instanceof PlutoDataError) {
      console.error(`[${err.code}] ${err.message}`);
      process.exit(2);
    }
    throw err;
  }
}

void main();
