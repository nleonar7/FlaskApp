import { describe, expect, it } from "vitest";
import {
  buildableFootprint,
  getDistrict,
  remainingFar,
  resolveFar,
} from "@/lib/zoning/rules";
import { detectFlags } from "@/lib/zoning/flags";
import { assembleFeasibility } from "@/lib/feasibility";
import { normalizeBbl } from "@/lib/pluto";
import { CONYINGHAM_GEOCODE, CONYINGHAM_LOT } from "./fixtures";

describe("getDistrict", () => {
  it("matches R3-1 (SPEC's first district)", () => {
    expect(getDistrict("R3-1")?.code).toBe("R3-1");
  });
  it("strips commercial-overlay / trailing tokens", () => {
    expect(getDistrict("R3-1 C1-2")?.code).toBe("R3-1");
  });
  it("returns null for out-of-scope districts (fail loud upstream)", () => {
    expect(getDistrict("R6")).toBeNull();
    expect(getDistrict(null)).toBeNull();
  });
});

describe("resolveFar", () => {
  it("prefers PLUTO.residfar over the rules table", () => {
    const d = getDistrict("R3-1");
    expect(resolveFar(0.5, d)).toEqual({ maxFar: 0.5, source: "PLUTO.residfar" });
  });
  it("falls back to the rules table when PLUTO FAR is missing", () => {
    const d = getDistrict("R3-1");
    expect(resolveFar(null, d)?.source).toBe("rules.maxResidFar");
  });
  it("returns null when neither is available", () => {
    expect(resolveFar(null, null)).toBeNull();
  });
});

describe("remainingFar", () => {
  it("computes max(0, far*lotarea - bldgarea)", () => {
    // 0.5 * 5000 - 1800 = 700
    const r = remainingFar(5000, 1800, 0.5, getDistrict("R3-1"));
    expect(r?.remainingSqft).toBe(700);
    expect(r?.isOverbuilt).toBe(false);
  });
  it("floors at 0 and flags over-built lots", () => {
    const r = remainingFar(5000, 3000, 0.5, getDistrict("R3-1")); // allowed 2500
    expect(r?.remainingSqft).toBe(0);
    expect(r?.isOverbuilt).toBe(true);
  });
  it("returns null without a lot area", () => {
    expect(remainingFar(null, 1800, 0.5, getDistrict("R3-1"))).toBeNull();
  });
});

describe("buildableFootprint", () => {
  it("subtracts required yards then applies the coverage cap", () => {
    const d = getDistrict("R3-1"); // front 15, rear 30, 2 side yards @ 5
    const fp = buildableFootprint(50, 100, 5000, d)!;
    // width 50 - 2*5 = 40; depth 100 - 15 - 30 = 55; 40*55 = 2200
    // coverage cap 0.35 * 5000 = 1750 -> binding
    expect(fp.usableWidthFt).toBe(40);
    expect(fp.usableDepthFt).toBe(55);
    expect(fp.coverageCapSqft).toBe(1750);
    expect(fp.footprintSqft).toBe(1750);
    expect(fp.limitedBy).toBe("lot-coverage");
  });
  it("states its rectangular-approximation assumptions (SPEC)", () => {
    const fp = buildableFootprint(50, 100, 5000, getDistrict("R3-1"))!;
    expect(fp.assumptions.length).toBeGreaterThan(0);
  });
  it("returns null without lot dimensions", () => {
    expect(buildableFootprint(null, 100, 5000, getDistrict("R3-1"))).toBeNull();
  });
});

describe("detectFlags", () => {
  it("flags Staten Island LDGMA and a pre-1961 build", () => {
    const ids = detectFlags(CONYINGHAM_LOT).map((f) => f.id);
    expect(ids).toContain("ldgma");
    expect(ids).toContain("pre-1961");
    expect(ids).toContain("plus-one-adu");
  });
});

describe("assembleFeasibility", () => {
  it("bundles district, envelope, footprint, and flags with no data gaps for a complete lot", () => {
    const f = assembleFeasibility(CONYINGHAM_GEOCODE, CONYINGHAM_LOT);
    expect(f.district?.code).toBe("R3-1");
    expect(f.remainingFar?.remainingSqft).toBe(700);
    expect(f.buildableFootprint).not.toBeNull();
    expect(f.dataGaps).toHaveLength(0);
  });

  it("records a data gap when the FAR is unavailable", () => {
    const f = assembleFeasibility(CONYINGHAM_GEOCODE, {
      ...CONYINGHAM_LOT,
      residfar: null,
      zonedist1: "R6", // out of table -> no rules FAR either
    });
    expect(f.remainingFar).toBeNull();
    expect(f.dataGaps.length).toBeGreaterThan(0);
  });
});

describe("normalizeBbl", () => {
  it("zero-pads to 10 chars and rejects non-numeric", () => {
    expect(normalizeBbl(5008130001)).toBe("5008130001");
    expect(normalizeBbl("813")).toBe("0000000813");
    expect(normalizeBbl("abc")).toBeNull();
    expect(normalizeBbl(null)).toBeNull();
  });
});
