"use client";

import { useEffect, useRef } from "react";

export type SurfacePollingResultGuard = () => boolean;

export function useVisibleSurfacePolling({
  enabled,
  intervalMs,
  poll
}: {
  enabled: boolean;
  intervalMs: number;
  poll: (isCurrent: SurfacePollingResultGuard) => Promise<void>;
}) {
  const pollRef = useRef(poll);
  const inFlightRef = useRef(false);
  const generationRef = useRef(0);

  useEffect(() => {
    pollRef.current = poll;
  }, [poll]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let disposed = false;
    const runPoll = async () => {
      if (disposed || document.visibilityState !== "visible" || inFlightRef.current) {
        return;
      }
      inFlightRef.current = true;
      const generation = ++generationRef.current;
      const isCurrent = () => (
        !disposed
        && document.visibilityState === "visible"
        && generation === generationRef.current
      );
      try {
        await pollRef.current(isCurrent);
      } finally {
        inFlightRef.current = false;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState !== "visible") {
        generationRef.current += 1;
        return;
      }
      void runPoll();
    };

    const interval = window.setInterval(() => void runPoll(), intervalMs);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      disposed = true;
      generationRef.current += 1;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled, intervalMs]);
}
