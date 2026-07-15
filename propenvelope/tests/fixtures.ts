import type { PlutoLot } from "@/lib/pluto";
import type { GeocodeResult } from "@/lib/pluto";

/**
 * Fixture based on the SPEC's reference address (60 Conyingham Ave, Staten
 * Island — an R3-1 lot). NUMBERS ARE ILLUSTRATIVE and should be replaced with
 * the real values from a live PLUTO fetch once verified:
 *   npm run pluto -- "60 Conyingham Ave, Staten Island, NY"
 * The rules-engine tests below exercise the *math*, which holds regardless of
 * the exact inputs.
 */
export const CONYINGHAM_GEOCODE: GeocodeResult = {
  bbl: "5008130001",
  label: "60 CONYINGHAM AVENUE, Staten Island, NY, USA",
  confidence: 0.99,
  borough: "Staten Island",
  lat: 40.6,
  lng: -74.09,
};

export const CONYINGHAM_LOT: PlutoLot = {
  bbl: "5008130001",
  borocode: 5,
  block: 813,
  lot: 1,
  address: "60 CONYINGHAM AVENUE",
  zipcode: "10301",
  zonedist1: "R3-1",
  landuse: "01", // 1-2 family residential
  bldgclass: "A1",
  lotarea: 5000,
  bldgarea: 1800,
  builtfar: 0.36,
  residfar: 0.5,
  commfar: null,
  facilfar: 1.0,
  lotfront: 50,
  lotdepth: 100,
  numfloors: 2,
  unitsres: 1,
  unitstotal: 1,
  yearbuilt: 1950,
  ownername: "DOE, JANE",
  version: "24v3",
};
