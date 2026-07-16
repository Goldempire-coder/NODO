"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const AdminWebEntryPage = dynamic(() => import("./AdminWebEntryPage").then((mod) => mod.AdminWebEntryPage), {
  ssr: false,
  loading: () => <main className="auth-entry"><section className="auth-entry__panel">Cargando Admin Web...</section></main>
});

const TelegramEntryPage = dynamic(() => import("./TelegramEntryPage").then((mod) => mod.TelegramEntryPage), {
  ssr: false,
  loading: () => <main className="auth-entry"><section className="auth-entry__panel">Preparando NODO...</section></main>
});

export function AuthEntryPage() {
  const [surface, setSurface] = useState<string | null>(null);

  useEffect(() => {
    setSurface(new URLSearchParams(window.location.search).get("surface") || "client");
  }, []);

  if (!surface) {
    return <main className="auth-entry"><section className="auth-entry__panel">Preparando NODO...</section></main>;
  }

  return surface === "admin" ? <AdminWebEntryPage /> : <TelegramEntryPage surface={surface} />;
}
