import type { FeasibilityInputs } from "@/lib/feasibility";
import { PLUTO_FIELD_SOURCES } from "@/lib/pluto";

/** A displayed value plus its PLUTO source field (SPEC: show provenance). */
function Field({
  label,
  value,
  source,
}: {
  label: string;
  value: string | number | null;
  source: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-slate-100 py-1.5">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-right">
        <span className="text-sm font-medium">
          {value === null || value === undefined ? "—" : value}
        </span>
        <span className="ml-2 text-[10px] uppercase tracking-wide text-slate-400">
          {source}
        </span>
      </span>
    </div>
  );
}

export function LotCard({ feasibility }: { feasibility: FeasibilityInputs }) {
  const { lot, geocode, district, remainingFar, buildableFootprint, flags, dataGaps } =
    feasibility;
  const s = PLUTO_FIELD_SOURCES;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Lot Snapshot</h2>
      <p className="mt-0.5 text-sm text-slate-500">
        {geocode.label} · BBL {lot.bbl} · match confidence{" "}
        {(geocode.confidence * 100).toFixed(0)}%
      </p>

      <div className="mt-4 grid gap-x-8 sm:grid-cols-2">
        <div>
          <Field label="Zoning district" value={lot.zonedist1} source={s.zonedist1} />
          <Field label="Land use" value={lot.landuse} source={s.landuse} />
          <Field label="Building class" value={lot.bldgclass} source={s.bldgclass} />
          <Field label="Lot area (sqft)" value={lot.lotarea} source={s.lotarea} />
          <Field label="Building area (sqft)" value={lot.bldgarea} source={s.bldgarea} />
        </div>
        <div>
          <Field label="Residential FAR" value={lot.residfar} source={s.residfar} />
          <Field label="Built FAR" value={lot.builtfar} source={s.builtfar} />
          <Field label="Lot frontage (ft)" value={lot.lotfront} source={s.lotfront} />
          <Field label="Lot depth (ft)" value={lot.lotdepth} source={s.lotdepth} />
          <Field label="Year built" value={lot.yearbuilt} source={s.yearbuilt} />
        </div>
      </div>

      <div className="mt-5 rounded-lg bg-slate-50 p-4">
        <h3 className="text-sm font-semibold">Remaining envelope</h3>
        {remainingFar ? (
          <p className="mt-1 text-sm text-slate-700">
            ~
            <span className="font-semibold">
              {Math.round(remainingFar.remainingSqft).toLocaleString()} sqft
            </span>{" "}
            of unused floor area (max FAR {remainingFar.maxFar} ×{" "}
            {lot.lotarea?.toLocaleString()} sqft − {remainingFar.builtFloorArea.toLocaleString()}{" "}
            built). FAR source: {remainingFar.farSource}.
            {remainingFar.isOverbuilt && " Note: currently over-built vs. allowed FAR."}
          </p>
        ) : (
          <p className="mt-1 text-sm text-amber-700">
            Remaining floor area could not be computed — see gaps below.
          </p>
        )}
        {buildableFootprint && (
          <p className="mt-2 text-sm text-slate-700">
            Rough buildable footprint ~
            <span className="font-semibold">
              {Math.round(buildableFootprint.footprintSqft).toLocaleString()} sqft
            </span>{" "}
            (limited by {buildableFootprint.limitedBy}).
          </p>
        )}
      </div>

      {district && !district.verified && (
        <p className="mt-3 text-xs text-amber-700">
          ⚠ {district.code} yard/height/coverage figures are provisional and not
          yet verified against the current Zoning Resolution.
        </p>
      )}

      {flags.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold">Flags</h3>
          <ul className="mt-1 space-y-1">
            {flags.map((f) => (
              <li key={f.id} className="text-sm text-slate-700">
                <span
                  className={
                    f.severity === "review"
                      ? "font-semibold text-red-700"
                      : f.severity === "caution"
                        ? "font-semibold text-amber-700"
                        : "font-semibold text-slate-700"
                  }
                >
                  {f.title}
                </span>{" "}
                — {f.detail}
                {f.link && (
                  <>
                    {" "}
                    <a
                      href={f.link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 underline"
                    >
                      details
                    </a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {dataGaps.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-amber-700">Data gaps</h3>
          <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
            {dataGaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
