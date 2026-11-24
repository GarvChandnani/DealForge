/**
 * DealForge Frontend — useHealth hook.
 *
 * Polls the backend /health endpoint every 30 seconds using React Query.
 */

import { useQuery } from "@tanstack/react-query";
import { healthApi } from "../api/client";
import type { HealthResponse } from "../types";

export function useHealth() {
  return useQuery<HealthResponse, Error>({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await healthApi.get();
      return data;
    },
    refetchInterval: 30_000,  // Re-poll every 30s
    retry: 2,
    staleTime: 10_000,
  });
}
