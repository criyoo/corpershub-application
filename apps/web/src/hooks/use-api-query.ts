"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type QueryState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
};

export function useApiQuery<T>(path: string, enabled = true, refreshIntervalMs?: number): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<T>(path);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load data.");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (enabled) {
      void refetch();
    }
  }, [enabled, refetch]);

  useEffect(() => {
    if (!enabled || !refreshIntervalMs) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refetch();
    }, refreshIntervalMs);

    return () => window.clearInterval(intervalId);
  }, [enabled, refreshIntervalMs, refetch]);

  return { data, loading, error, refetch };
}
