/**
 * Deterministic feasibility bundle: everything the report LLM is allowed to
 * narrate. The LLM receives ONLY this object plus the interview JSON — it must
 * not introduce any zoning number that isn't here (SPEC non-negotiable).
 */

import { lookupByAddress, type GeocodeResult, type PlutoLot } from "@/lib/pluto";
import {
  buildableFootprint,
  getDistrict,
  remainingFar,
  type BuildableFootprint,
  type RemainingFar,
  type ZoningDistrict,
} from "@/lib/zoning/rules";
import { detectFlags, type Flag } from "@/lib/zoning/flags";

export interface FeasibilityInputs {
  geocode: GeocodeResult;
  lot: PlutoLot;
  district: ZoningDistrict | null;
  /** Present when we could compute it; null (with a flag) when we couldn't. */
  remainingFar: RemainingFar | null;
  buildableFootprint: BuildableFootprint | null;
  flags: Flag[];
  /** Notes about missing/unknown inputs — the report must not paper over these. */
  dataGaps: string[];
}

/** Address string -> full deterministic feasibility bundle. Throws PlutoDataError. */
export async function computeFeasibility(
  address: string,
): Promise<FeasibilityInputs> {
  const { geocode, lot } = await lookupByAddress(address);
  return assembleFeasibility(geocode, lot);
}

/** Pure assembly step — split out so tests can feed a fixture lot directly. */
export function assembleFeasibility(
  geocode: GeocodeResult,
  lot: PlutoLot,
): FeasibilityInputs {
  const district = getDistrict(lot.zonedist1);
  const dataGaps: string[] = [];

  if (!district) {
    dataGaps.push(
      `Zoning district "${lot.zonedist1 ?? "(none)"}" (PLUTO.zonedist1) is not ` +
        "in the v1 low-density table — yard/coverage rules unavailable.",
    );
  }
  if (lot.lotarea == null) dataGaps.push("PLUTO.lotarea missing — cannot size FAR.");
  if (lot.residfar == null && district?.maxResidFar == null) {
    dataGaps.push("No residential FAR from PLUTO or rules table.");
  }
  if (lot.lotfront == null || lot.lotdepth == null) {
    dataGaps.push(
      "PLUTO.lotfront/lotdepth missing — buildable footprint not estimated.",
    );
  }

  const far = remainingFar(lot.lotarea, lot.bldgarea, lot.residfar, district);
  const footprint = buildableFootprint(
    lot.lotfront,
    lot.lotdepth,
    lot.lotarea,
    district,
  );

  return {
    geocode,
    lot,
    district,
    remainingFar: far,
    buildableFootprint: footprint,
    flags: detectFlags(lot),
    dataGaps,
  };
}
