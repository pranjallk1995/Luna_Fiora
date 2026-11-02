/** The backend routes the gateway forwards, and the React Query hooks over them. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { post, request } from "./http";

export type Row = Record<string, unknown>;

export type Dashboard = {
  analytics: {
    income: number;
    expense: number;
    net: number;
    categories: { category: string; total: number }[];
    trend: { day: string; income: number; expense: number }[];
  };
  transactions: Row[];
  commitments: Row[];
  goals: Row[];
  reminders: Row[];
};

export type DateRange = { start: string; end: string };
export type Resource = "transactions" | "commitments" | "goals" | "reminders";

export function useDashboard({ start, end }: DateRange) {
  return useQuery({
    queryKey: ["dashboard", start, end],
    queryFn: () =>
      request<Dashboard>(`/api/dashboard?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
    placeholderData: (previous) => previous,
  });
}

export function useCreate(resource: Resource) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Row) => post(`/api/${resource}`, payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  });
}

export function useGmailLink() {
  return useQuery({
    queryKey: ["gmail-link"],
    queryFn: () => request<{ url: string }>("/api/gmail/authorization-url"),
    retry: false,
    // Each link carries a signed state that expires, so fetch a fresh one every visit.
    staleTime: 0,
    gcTime: 0,
  });
}

export function useGmailSync() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      post<{ configured: boolean; imported: number; review: number }>("/api/gmail/sync"),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  });
}
