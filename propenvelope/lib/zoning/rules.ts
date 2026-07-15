/**
 * NYC low-density residential zoning rules engine (deterministic, no LLM).
 *
 * SPEC non-negotiable: all zoning math lives here in TypeScript; the LLM only
 * narrates numbers this module produces. It never invents them.
 *
 * ---------------------------------------------------------------------------
 * DATA-PROVENANCE WARNING
 * ---------------------------------------------------------------------------
 * The per-district bulk/yard/height/coverage figures below are transcribed
 * from the NYC Zoning Resolution (Article II) and are marked `verified: false`
 * until each is checked against the *current* ZR text at build time. FAR values
 * are the most stable and are additionally cross-checked at runtime against
 * PLUTO's `residfar` for the actual lot (see `resolveFar`). Yard/height/coverage
 * figures are the ones most likely to be wrong or district-variant-specific —
 * treat any `verified: false` district as provisional and surface that to the
 * user rather than presenting it as authoritative. When a needed figure is
 * unknown we store `null` and the report must flag it, never guess (fail loud).
 *
 * Reference: NYC Zoning Resolution Article II, Chapters 2–3
 * (https://zr.planning.nyc.gov/article-ii). Verify before production use.
 */

export type BuildingArrangement =
  | "detached"
  | "semi-detached"
  | "attached"
  | "any";

export interface ZoningDistrict {
  /** Canonical district code as it appears in PLUTO.zonedist1, e.g. "R3-1". */
  code: string;
  label: string;
  /** Max residential FAR per ZR. PLUTO.residfar is authoritative per-lot. */
  maxResidFar: number | null;
  /** Max fraction of the lot the building footprint may cover (0..1), or null. */
  maxLotCoverage: number | null;
  /** Minimum front yard depth, feet. */
  frontYardMinFt: number | null;
  /** Minimum depth of EACH required side yard, feet (null if none required). */
  sideYardMinFt: number | null;
  /** Number of side yards the arrangement requires (0, 1, or 2). */
  requiredSideYards: number | null;
  /** Minimum rear yard depth, feet. */
  rearYardMinFt: number | null;
  /** Max building (or perimeter-wall) height, feet. */
  maxBuildingHeightFt: number | null;
  /** Off-street parking spaces required per dwelling unit. */
  parkingPerUnit: number | null;
  /** Typical permitted building arrangement for the district. */
  arrangement: BuildingArrangement;
  /** False until the figures are checked against the current ZR. */
  verified: boolean;
  /** Free-text provenance / caveats for the report's Flags section. */
  sourceNote: string;
}

/**
 * Low-density districts, Staten Island coverage first (SPEC step order).
 * FAR values are widely published and stable; yard/height/coverage are
 * PROVISIONAL (verified:false) pending a ZR check.
 */
export const DISTRICTS: Record<string, ZoningDistrict> = {
  "R1-2": {
    code: "R1-2",
    label: "R1-2 — detached single-family, large lots",
    maxResidFar: 0.5,
    maxLotCoverage: null,
    frontYardMinFt: 20,
    sideYardMinFt: 8,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. FAR stable; yards/height provisional.",
  },
  R2: {
    code: "R2",
    label: "R2 — detached single-family",
    maxResidFar: 0.5,
    maxLotCoverage: null,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. FAR stable; yards/height provisional.",
  },
  "R3-1": {
    code: "R3-1",
    label: "R3-1 — detached & semi-detached 1–2 family",
    maxResidFar: 0.5, // 0.6 available via attic allowance; base is 0.5
    maxLotCoverage: 0.35,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote:
      "ZR Art. II Ch. 2–3. Base FAR 0.5 (0.6 w/ attic allowance). Yards/height provisional.",
  },
  "R3-2": {
    code: "R3-2",
    label: "R3-2 — general low-density, all building types",
    maxResidFar: 0.5, // 0.6 with attic allowance
    maxLotCoverage: 0.35,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "any",
    verified: false,
    sourceNote:
      "ZR Art. II Ch. 2–3. Base FAR 0.5 (0.6 w/ attic allowance). Yards/height provisional.",
  },
  R3A: {
    code: "R3A",
    label: "R3A — detached, contextual",
    maxResidFar: 0.5,
    maxLotCoverage: 0.35,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. Contextual district. Yards/height provisional.",
  },
  R3X: {
    code: "R3X",
    label: "R3X — detached, lower bulk contextual",
    maxResidFar: 0.5,
    maxLotCoverage: 0.35,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. Contextual district. Yards/height provisional.",
  },
  R4: {
    code: "R4",
    label: "R4 — low-density, all building types",
    maxResidFar: 0.75, // 0.9 with attic allowance
    maxLotCoverage: 0.45,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "any",
    verified: false,
    sourceNote:
      "ZR Art. II Ch. 2–3. Base FAR 0.75 (0.9 w/ attic allowance). Yards/height provisional.",
  },
  "R4-1": {
    code: "R4-1",
    label: "R4-1 — detached & semi-detached",
    maxResidFar: 0.75,
    maxLotCoverage: 0.45,
    frontYardMinFt: 15,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 35,
    parkingPerUnit: 1,
    arrangement: "detached",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. Yards/height provisional.",
  },
  R5: {
    code: "R5",
    label: "R5 — moderate low-density",
    maxResidFar: 1.25,
    maxLotCoverage: 0.55,
    frontYardMinFt: 10,
    sideYardMinFt: 5,
    requiredSideYards: 2,
    rearYardMinFt: 30,
    maxBuildingHeightFt: 40,
    parkingPerUnit: 0.85,
    arrangement: "any",
    verified: false,
    sourceNote: "ZR Art. II Ch. 2–3. Yards/height provisional.",
  },
};

/**
 * Look up a district by PLUTO.zonedist1. NYC zonedist1 values can carry a
 * commercial-overlay suffix or extra text; we match the base district token.
 * Returns null for districts not in our v1 table (report must flag "out of
 * scope" rather than guess).
 */
export function getDistrict(zonedist1: string | null): ZoningDistrict | null {
  if (!zonedist1) return null;
  const token = zonedist1.trim().toUpperCase().split(/\s+/)[0];
  return DISTRICTS[token] ?? null;
}

// --- envelope math ---------------------------------------------------------

export interface RemainingFar {
  maxFar: number;
  farSource: "PLUTO.residfar" | "rules.maxResidFar";
  maxFloorArea: number; // maxFar * lotarea, sqft
  builtFloorArea: number; // PLUTO.bldgarea, sqft
  remainingSqft: number; // max(0, maxFloorArea - builtFloorArea)
  isOverbuilt: boolean; // built > allowed (e.g. grandfathered)
}

/**
 * Decide which FAR to trust: PLUTO's per-lot `residfar` is authoritative and
 * preferred; the rules-table value is a fallback/cross-check. Returns null if
 * neither is available (caller must fail loud).
 */
export function resolveFar(
  plutoResidFar: number | null,
  district: ZoningDistrict | null,
): { maxFar: number; source: RemainingFar["farSource"] } | null {
  if (plutoResidFar !== null && plutoResidFar > 0) {
    return { maxFar: plutoResidFar, source: "PLUTO.residfar" };
  }
  if (district?.maxResidFar != null && district.maxResidFar > 0) {
    return { maxFar: district.maxResidFar, source: "rules.maxResidFar" };
  }
  return null;
}

/**
 * remainingFAR_sqft = max(0, maxFar * lotarea - bldgarea).
 * Returns null if inputs are missing (fail loud upstream).
 */
export function remainingFar(
  lotArea: number | null,
  bldgArea: number | null,
  plutoResidFar: number | null,
  district: ZoningDistrict | null,
): RemainingFar | null {
  if (lotArea == null || lotArea <= 0) return null;
  const far = resolveFar(plutoResidFar, district);
  if (!far) return null;

  const built = bldgArea ?? 0;
  const maxFloorArea = far.maxFar * lotArea;
  const remainingSqft = Math.max(0, maxFloorArea - built);
  return {
    maxFar: far.maxFar,
    farSource: far.source,
    maxFloorArea,
    builtFloorArea: built,
    remainingSqft,
    isOverbuilt: built > maxFloorArea,
  };
}

export interface BuildableFootprint {
  lotFrontFt: number;
  lotDepthFt: number;
  usableWidthFt: number; // lotFront - 2*sideYard
  usableDepthFt: number; // lotDepth - frontYard - rearYard
  footprintSqft: number; // usableWidth * usableDepth, floored at 0
  coverageCapSqft: number | null; // maxLotCoverage * lotarea, if a cap exists
  /** The binding constraint: yards, the coverage cap, or none computed. */
  limitedBy: "yards" | "lot-coverage" | "unknown";
  assumptions: string[];
}

/**
 * Rectangular-approximation buildable footprint: subtract required yards from
 * the lot rectangle, then apply the max-lot-coverage cap if the district has
 * one. SPEC says a rectangular approximation is fine for v1 as long as we state
 * the assumption — we return them in `assumptions`. Returns null if we lack lot
 * dimensions (fail loud).
 */
export function buildableFootprint(
  lotFront: number | null,
  lotDepth: number | null,
  lotArea: number | null,
  district: ZoningDistrict | null,
): BuildableFootprint | null {
  if (lotFront == null || lotFront <= 0 || lotDepth == null || lotDepth <= 0) {
    return null;
  }

  const assumptions: string[] = [
    "Lot treated as a rectangle (PLUTO.lotfront × PLUTO.lotdepth); irregular lots differ.",
    "Required yards subtracted symmetrically; actual placement may vary.",
  ];

  const sideYard = district?.sideYardMinFt ?? 0;
  const sides = district?.requiredSideYards ?? 0;
  const frontYard = district?.frontYardMinFt ?? 0;
  const rearYard = district?.rearYardMinFt ?? 0;

  if (!district || !district.verified) {
    assumptions.push(
      "Yard figures are PROVISIONAL (not yet verified against the current Zoning Resolution).",
    );
  }

  const usableWidthFt = Math.max(0, lotFront - sideYard * sides);
  const usableDepthFt = Math.max(0, lotDepth - frontYard - rearYard);
  let footprintSqft = usableWidthFt * usableDepthFt;
  let limitedBy: BuildableFootprint["limitedBy"] =
    district ? "yards" : "unknown";

  let coverageCapSqft: number | null = null;
  if (district?.maxLotCoverage != null && lotArea != null && lotArea > 0) {
    coverageCapSqft = district.maxLotCoverage * lotArea;
    if (coverageCapSqft < footprintSqft) {
      footprintSqft = coverageCapSqft;
      limitedBy = "lot-coverage";
    }
  }

  return {
    lotFrontFt: lotFront,
    lotDepthFt: lotDepth,
    usableWidthFt,
    usableDepthFt,
    footprintSqft,
    coverageCapSqft,
    limitedBy,
    assumptions,
  };
}
