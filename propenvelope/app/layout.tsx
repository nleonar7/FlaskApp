import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PropEnvelope — NYC Property Feasibility",
  description:
    "Enter a NYC address, describe what you want to build, and get a zoning feasibility report grounded in official NYC open data.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <div className="mx-auto max-w-3xl px-4 py-8">{children}</div>
      </body>
    </html>
  );
}
