"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, toTransportError } from "@/lib/api/errors";

export type AsyncStatus = "loading" | "success" | "error";

export interface AsyncResource<T> {
  data: T | null;
  error: ApiError | null;
  status: AsyncStatus;
  /** True while a refresh runs on top of data that is already displayed. */
  isRefreshing: boolean;
  reload: () => void;
}

/**
 * Runs an abortable loader and keeps the previous value visible during a
 * refresh, so the layout does not collapse back to a skeleton.
 */
export function useAsyncResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [nonce, setNonce] = useState(0);

  const hasDataRef = useRef(false);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    if (hasDataRef.current) {
      setIsRefreshing(true);
    } else {
      setStatus("loading");
    }

    loaderRef
      .current(controller.signal)
      .then((result) => {
        if (!active) return;
        hasDataRef.current = true;
        setData(result);
        setError(null);
        setStatus("success");
      })
      .catch((cause: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(toTransportError(cause));
        setStatus("error");
      })
      .finally(() => {
        if (active) setIsRefreshing(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  return { data, error, status, isRefreshing, reload };
}
