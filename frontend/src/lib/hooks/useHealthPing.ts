"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchHealth } from "@/lib/api/health";

export type ConnectionState = "checking" | "online" | "offline";

/**
 * Optional connection indicator. The integration doc caps polling at once
 * every 30 seconds, so that is the floor enforced here.
 */
export function useHealthPing(intervalMs = 30_000): {
  state: ConnectionState;
  checkNow: () => void;
} {
  const [state, setState] = useState<ConnectionState>("checking");
  const [nonce, setNonce] = useState(0);
  const safeInterval = Math.max(intervalMs, 30_000);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkNow = useCallback(() => setNonce((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const ping = async () => {
      try {
        const result = await fetchHealth(controller.signal);
        if (active) setState(result.status === "ok" ? "online" : "offline");
      } catch {
        if (active) setState("offline");
      }
    };

    void ping();
    timerRef.current = setInterval(ping, safeInterval);

    return () => {
      active = false;
      controller.abort();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [safeInterval, nonce]);

  return { state, checkNow };
}
