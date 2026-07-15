/**
 * Special-case detectors. Per SPEC these SURFACE issues for human review —
 * they never try to resolve them. Each flag is advisory and points the user at
 * the right professional or official resource.
 */

import type { PlutoLot } from "@/lib/pluto";
import { getDistrict } from "@/lib/zoning/rules";

export type FlagSeverity = "info" | "caution" | "review";

export interface Flag {
  id: string;
  severity: FlagSeverity;
  title: string;
  detail: string;
  /** Optional official link the user should consult. */
  link?: string;
}

/** NYC Plus One ADU program — official info page (link, don't assert eligibility). */
const PLUS_ONE_ADU_URL = "https://www.nyc.gov/adu";
/** DOB building-class reference. */
const BLDG_CLASS_URL =
  "https://www.nyc.gov/assets/finance/jump/hlpbldgcode.html";

/** Building-class prefixes that indicate attached / semi-detached forms. */
const ATTACHED_BLDG_CLASSES = new Set(["A5", "A9", "B1", "B9", "C0"]);

/**
 * Run every detector against a lot. Order is stable so the report is
 * deterministic. Returns [] when nothing special is detected.
 */
export function detectFlags(lot: PlutoLot): Flag[] {
  const flags: Flag[] = [];

  // 1. Lower Density Growth Management Area — all of Staten Island (borocode 5).
  if (lot.borocode === 5) {
    flags.push({
      id: "ldgma",
      severity: "caution",
      title: "Lower Density Growth Management Area (Staten Island)",
      detail:
        "All of Staten Island is an LDGMA, which modifies yard, parking, and " +
        "density requirements beyond the base district. Envelope figures here " +
        "do not yet apply LDGMA overrides — confirm with an architect/expediter.",
    });
  }

  // 2. Pre-existing non-conforming structure (grandfathering review).
  //    NYC's comprehensive zoning resolution took effect in 1961; buildings
  //    predating it are commonly non-conforming in some respect.
  if (lot.yearbuilt != null && lot.yearbuilt > 0 && lot.yearbuilt < 1961) {
    flags.push({
      id: "pre-1961",
      severity: "review",
      title: "Pre-1961 structure — grandfathering review recommended",
      detail:
        `Built ${lot.yearbuilt} (PLUTO.yearbuilt), before the 1961 Zoning ` +
        "Resolution. It may legally exceed current bulk/yard limits as a " +
        "non-conforming structure; additions can trigger conformance review.",
    });
  }

  // 3. Over-built vs. current FAR (another grandfathering signal).
  if (
    lot.builtfar != null &&
    lot.residfar != null &&
    lot.residfar > 0 &&
    lot.builtfar > lot.residfar + 0.01
  ) {
    flags.push({
      id: "overbuilt-far",
      severity: "review",
      title: "Already exceeds current residential FAR",
      detail:
        `Built FAR ${lot.builtfar} (PLUTO.builtfar) is above the ${lot.residfar} ` +
        "residential FAR (PLUTO.residfar). Likely non-conforming/grandfathered — " +
        "enlargements may be restricted.",
    });
  }

  // 4. Attached / semi-detached building class (affects side-yard math).
  if (lot.bldgclass) {
    const prefix = lot.bldgclass.trim().toUpperCase().slice(0, 2);
    if (ATTACHED_BLDG_CLASSES.has(prefix)) {
      flags.push({
        id: "attached",
        severity: "caution",
        title: "Attached / semi-detached building",
        detail:
          `Building class ${lot.bldgclass} (PLUTO.bldgclass) indicates an ` +
          "attached or semi-detached form. Side-yard assumptions in the " +
          "envelope estimate may not apply.",
        link: BLDG_CLASS_URL,
      });
    }
  }

  // 5. NYC Plus One ADU heuristic — 1–2 family residential. LINK only; we do
  //    NOT assert eligibility (SPEC).
  const district = getDistrict(lot.zonedist1);
  const isLowDensityRes = district != null;
  const oneOrTwoFamily =
    lot.unitsres != null && lot.unitsres >= 1 && lot.unitsres <= 2;
  if (isLowDensityRes && oneOrTwoFamily) {
    flags.push({
      id: "plus-one-adu",
      severity: "info",
      title: "May fit the NYC Plus One ADU program",
      detail:
        "This looks like a 1–2 family home in a low-density district — the " +
        "profile the NYC Plus One ADU program targets. Eligibility depends on " +
        "owner-occupancy and the current pilot boroughs; confirm on the official page.",
      link: PLUS_ONE_ADU_URL,
    });
  }

  return flags;
}
