"use client";

import { useCallback, useRef } from "react";

type StableKeyEntry = {
  key: string;
  signature: string;
};

function stableJson(value: unknown): string {
  if (value === undefined) {
    return "undefined";
  }
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJson(item)).join(",")}]`;
  }
  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`)
    .join(",")}}`;
}

export function createIdempotencyKey(scope: string) {
  const randomId =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : Math.random().toString(16).slice(2);
  return `${scope}_${randomId}`;
}

export function useStableIdempotencyKeys() {
  const entriesRef = useRef<Map<string, StableKeyEntry>>(new Map());

  const getIdempotencyKey = useCallback((scope: string, signatureInput?: unknown) => {
    const signature = stableJson(signatureInput ?? null);
    const current = entriesRef.current.get(scope);
    if (current && current.signature === signature) {
      return current.key;
    }
    const entry = { key: createIdempotencyKey(scope), signature };
    entriesRef.current.set(scope, entry);
    return entry.key;
  }, []);

  const clearIdempotencyKey = useCallback((scope: string) => {
    entriesRef.current.delete(scope);
  }, []);

  return { clearIdempotencyKey, getIdempotencyKey };
}
