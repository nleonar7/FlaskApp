/**
 * PLUTO + GeoSearch data layer.
 *
 * Two free NYC services, no API keys:
 *   1. NYC GeoSearch (https://geosearch.planninglabs.nyc) — address -> BBL.
 *   2. NYC Open Data PLUTO (Socrata dataset 64uk-42ks) — BBL -> tax-lot facts.
 *
 * Ported from the Flask app's `flaskblog/ranking/pluto.py` (resolve_bbl) and
 * `flaskblog/pluto/ingest.py` (field mapping). Unlike the Flask app we do NOT
 * bulk-load a database: v1 fetches a single lot live, per request, and fails
 * loudly when the data is missing rather than guessing (SPEC non-negotiable).
 *
 * Every field carries its PLUTO source name via PLUTO_FIELD_SOURCES so the UI
 * can show provenance for each displayed value (SPEC non-negotiable).
 */

const GEOSEARCH_URL = "https://geosearch.planninglabs.nyc/v2/search";
const SOCRATA_URL = "https://data.cityofnewyork.us/resource/64uk-42ks.json";

/** Minimum GeoSearch confidence we accept for an address->BBL match. */
const MIN_CONFIDENCE = 0.7;

/** Raised when a data source is unreachable, empty, or below confidence. */
export class PlutoDataError extends Error {
  readonly code:
    | "geosearch_unreachable"
    | "no_address_match"
    | "low_confidence"
    | "no_bbl"
    | "pluto_unreachable"
    | "lot_not_found";

  constructor(code: PlutoDataError["code"], message: string) {
    super(message);
    this.name = "PlutoDataError";
    this.code = code;
  }
}

/** A resolved address with its BBL and match confidence. */
export interface GeocodeResult {
  bbl: string; // 10-char, zero-padded (leading zeros are significant)
  label: string; // GeoSearch's formatted label for the matched address
  confidence: number;
  borough: string | null;
  lat: number | null;
  lng: number | null;
}

/**
 * The PLUTO fields v1 relies on. Names mirror the Socrata columns exactly so
 * we can show the source field to the user. Numeric fields are numbers or null;
 * strings are strings or null. `bbl` is always present (it's the key).
 */
export interface PlutoLot {
  bbl: string;
  borocode: number | null;
  block: number | null;
  lot: number | null;
  address: string | null;
  zipcode: string | null;
  zonedist1: string | null;
  landuse: string | null;
  bldgclass: string | null;
  lotarea: number | null;
  bldgarea: number | null;
  builtfar: number | null;
  residfar: number | null;
  commfar: number | null;
  facilfar: number | null;
  lotfront: number | null;
  lotdepth: number | null;
  numfloors: number | null;
  unitsres: number | null;
  unitstotal: number | null;
  yearbuilt: number | null;
  ownername: string | null;
  version: string | null; // PLUTO release version — used to warn on staleness
}

/** Human-facing provenance: which PLUTO column backs each displayed value. */
export const PLUTO_FIELD_SOURCES: Record<keyof PlutoLot, string> = {
  bbl: "PLUTO.bbl",
  borocode: "PLUTO.borocode",
  block: "PLUTO.block",
  lot: "PLUTO.lot",
  address: "PLUTO.address",
  zipcode: "PLUTO.zipcode",
  zonedist1: "PLUTO.zonedist1",
  landuse: "PLUTO.landuse",
  bldgclass: "PLUTO.bldgclass",
  lotarea: "PLUTO.lotarea",
  bldgarea: "PLUTO.bldgarea",
  builtfar: "PLUTO.builtfar",
  residfar: "PLUTO.residfar",
  commfar: "PLUTO.commfar",
  facilfar: "PLUTO.facilfar",
  lotfront: "PLUTO.lotfront",
  lotdepth: "PLUTO.lotdepth",
  numfloors: "PLUTO.numfloors",
  unitsres: "PLUTO.unitsres",
  unitstotal: "PLUTO.unitstotal",
  yearbuilt: "PLUTO.yearbuilt",
  ownername: "PLUTO.ownername",
  version: "PLUTO.version",
};

// --- address -> BBL --------------------------------------------------------

/**
 * Resolve a street address to a BBL via NYC GeoSearch. Throws PlutoDataError
 * on network failure, no match, or a match below MIN_CONFIDENCE — we never
 * silently return a guess.
 */
export async function geocodeToBbl(address: string): Promise<GeocodeResult> {
  const text = address.trim();
  if (!text) {
    throw new PlutoDataError("no_address_match", "Empty address.");
  }

  const url = `${GEOSEARCH_URL}?text=${encodeURIComponent(text)}`;
  let features: any[];
  try {
    const resp = await fetch(url, { signal: AbortSignal.timeout(15_000) });
    if (!resp.ok) {
      throw new PlutoDataError(
        "geosearch_unreachable",
        `GeoSearch returned HTTP ${resp.status}.`,
      );
    }
    const body = await resp.json();
    features = body?.features ?? [];
  } catch (err) {
    if (err instanceof PlutoDataError) throw err;
    throw new PlutoDataError(
      "geosearch_unreachable",
      `GeoSearch request failed: ${(err as Error).message}`,
    );
  }

  if (features.length === 0) {
    throw new PlutoDataError(
      "no_address_match",
      `No NYC address match for "${text}".`,
    );
  }

  const top = features[0];
  const props = top?.properties ?? {};
  const confidence: number = props.confidence ?? 0;
  const rawBbl = props?.addendum?.pad?.bbl;
  const bbl = normalizeBbl(rawBbl);

  if (!bbl) {
    throw new PlutoDataError(
      "no_bbl",
      `GeoSearch matched "${props.label ?? text}" but returned no BBL.`,
    );
  }
  if (confidence < MIN_CONFIDENCE) {
    throw new PlutoDataError(
      "low_confidence",
      `Best match "${props.label ?? text}" scored ${confidence.toFixed(
        2,
      )} < ${MIN_CONFIDENCE}. Refine the address.`,
    );
  }

  const [lng, lat] = top?.geometry?.coordinates ?? [null, null];
  return {
    bbl,
    label: props.label ?? text,
    confidence,
    borough: props.borough ?? null,
    lat: typeof lat === "number" ? lat : null,
    lng: typeof lng === "number" ? lng : null,
  };
}

// --- BBL -> PLUTO lot ------------------------------------------------------

/**
 * Fetch a single PLUTO lot by BBL from Socrata. Throws PlutoDataError if the
 * service is unreachable or the lot isn't in the dataset (fail loud, SPEC).
 */
export async function fetchPlutoLot(bbl: string): Promise<PlutoLot> {
  const normalized = normalizeBbl(bbl);
  if (!normalized) {
    throw new PlutoDataError("lot_not_found", `Invalid BBL: "${bbl}".`);
  }

  // Socrata stores bbl as a number; compare numerically to dodge zero-padding.
  const where = `bbl=${Number(normalized)}`;
  const url = `${SOCRATA_URL}?$where=${encodeURIComponent(where)}&$limit=1`;

  const headers: Record<string, string> = {};
  const token = process.env.SOCRATA_APP_TOKEN;
  if (token) headers["X-App-Token"] = token;

  let rows: any[];
  try {
    const resp = await fetch(url, {
      headers,
      signal: AbortSignal.timeout(20_000),
    });
    if (!resp.ok) {
      throw new PlutoDataError(
        "pluto_unreachable",
        `PLUTO/Socrata returned HTTP ${resp.status}.`,
      );
    }
    rows = await resp.json();
  } catch (err) {
    if (err instanceof PlutoDataError) throw err;
    throw new PlutoDataError(
      "pluto_unreachable",
      `PLUTO request failed: ${(err as Error).message}`,
    );
  }

  if (!Array.isArray(rows) || rows.length === 0) {
    throw new PlutoDataError(
      "lot_not_found",
      `No PLUTO lot for BBL ${normalized}.`,
    );
  }

  return mapPlutoRow(rows[0], normalized);
}

/** Convenience: address -> BBL -> lot in one call. */
export async function lookupByAddress(
  address: string,
): Promise<{ geocode: GeocodeResult; lot: PlutoLot }> {
  const geocode = await geocodeToBbl(address);
  const lot = await fetchPlutoLot(geocode.bbl);
  return { geocode, lot };
}

// --- internals -------------------------------------------------------------

/** Zero-pad and validate a BBL to the canonical 10-digit string, or null. */
export function normalizeBbl(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  const text = String(value).split(".")[0].trim(); // drop any ".0"
  if (!/^\d+$/.test(text)) return null;
  return text.padStart(10, "0");
}

function mapPlutoRow(raw: Record<string, unknown>, bbl: string): PlutoLot {
  return {
    bbl,
    borocode: toInt(raw.borocode),
    block: toInt(raw.block),
    lot: toInt(raw.lot),
    address: toStr(raw.address),
    zipcode: toStr(raw.zipcode),
    zonedist1: toStr(raw.zonedist1),
    landuse: toStr(raw.landuse),
    bldgclass: toStr(raw.bldgclass),
    lotarea: toInt(raw.lotarea),
    bldgarea: toInt(raw.bldgarea),
    builtfar: toFloat(raw.builtfar),
    residfar: toFloat(raw.residfar),
    commfar: toFloat(raw.commfar),
    facilfar: toFloat(raw.facilfar),
    lotfront: toFloat(raw.lotfront),
    lotdepth: toFloat(raw.lotdepth),
    numfloors: toFloat(raw.numfloors),
    unitsres: toInt(raw.unitsres),
    unitstotal: toInt(raw.unitstotal),
    yearbuilt: toInt(raw.yearbuilt),
    ownername: toStr(raw.ownername),
    version: toStr(raw.version),
  };
}

function toInt(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function toFloat(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toStr(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const s = String(value).trim();
  return s === "" ? null : s;
}
